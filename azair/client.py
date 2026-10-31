import asyncio
import httpx
import re
from urllib.parse import urlencode
from .metros import METRO_AIRPORTS
from .models import FlightResult, SearchParams
from .parser import parse_results


BASE_URL = "https://www.azair.eu"
SEARCH_URL = f"{BASE_URL}/azfin.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _normalize_date(d: str) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        parts = d.split("-")
        return f"{parts[2]}.{parts[1]}.{parts[0]}"
    return d


def _weekday_bit(departure: list[int] | None, ret: list[int] | None) -> dict[str, str]:
    dep_days = set(departure) if departure else set(range(7))
    arr_days = set(ret) if ret else set(range(7))
    bits = {}
    for i in range(7):
        bits[f"dep{i}"] = "true" if i in dep_days else "false"
        bits[f"arr{i}"] = "true" if i in arr_days else "false"
    return bits


AIRPORT_CODE_RE = re.compile(r"^[A-Z]{3}$")


def _expand_extra_codes(extras: list[str] | None) -> list[str]:
    result = []
    for raw in extras or []:
        code = (raw or "").strip().upper()
        if not code or code == "XXX":
            continue
        if code in METRO_AIRPORTS:
            result.extend(METRO_AIRPORTS[code][1])
        elif AIRPORT_CODE_RE.match(code):
            result.append(code)
    return result


def _dedupe_extras(main_code: str, extras: list[str] | None) -> list[str]:
    seen = {main_code.upper()}
    result = []
    for code in _expand_extra_codes(extras):
        if code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result


def _expand_airport(
    main_code: str,
    extras: list[str] | None,
    metro_code: str | None,
) -> tuple[str, list[str], str | None]:
    """Expand metro/region codes into a primary airport plus extra airports.

    azair only searches the airports listed in the ``srcAirport``/``dstAirport``
    string and the ``srcapN``/``dstapN`` params. Passing a metro code such as
    ``MIL_ALL`` directly in the airport field does not work, so it has to be
    translated into its airports first.
    """
    code = (main_code or "").strip().upper()
    extras = [(c or "").strip().upper() for c in (extras or []) if (c or "").strip()]
    metro_code = (metro_code or "").strip().upper() or None

    if code == "XXX":
        return code, [], None

    if code in METRO_AIRPORTS:
        ports = METRO_AIRPORTS[code][1]
        main = ports[0]
        extras = ports[1:] + extras
        return main, _dedupe_extras(main, extras), code

    if metro_code in METRO_AIRPORTS and metro_code != "XXX":
        ports = METRO_AIRPORTS[metro_code][1]
        main = code if code in ports else ports[0]
        extras = [p for p in ports if p != main] + extras
        return main, _dedupe_extras(main, extras), metro_code

    return code, _dedupe_extras(code, extras), None


def _airport_value(main_code: str, extras: list[str]) -> str:
    if not extras:
        return f"[{main_code}]"
    return f"[{main_code}] (+{','.join(extras)})"


def _extra_params(prefix: str, extras: list[str]) -> dict[str, str]:
    return {f"{prefix}ap{i}": code for i, code in enumerate(extras)}


def _typed_text(main_code: str, metro_code: str | None) -> str:
    if main_code == "XXX":
        return "anyw"
    if metro_code:
        return metro_code.split("_")[0].lower()[:3]
    return main_code.lower()[:3]


def build_search_url(params: SearchParams) -> str:
    dep = _normalize_date(params.dep_date)
    arr = _normalize_date(params.arr_date)
    weekday_bits = _weekday_bit(params.departure_weekdays, params.return_weekdays)
    src_main, src_extras, src_mc = _expand_airport(
        params.src_airport, params.src_airports, params.src_metro_code
    )
    dst_main, dst_extras, dst_mc = _expand_airport(
        params.dst_airport, params.dst_airports, params.dst_metro_code
    )

    query = {
        "searchtype": "flexi",
        "tp": "0",
        "srcAirport": _airport_value(src_main, src_extras),
        "srcTypedText": _typed_text(src_main, src_mc),
        "srcFreeTypedText": "",
        "srcMC": src_mc or "",
        "srcFreeAirport": "",
        "dstAirport": _airport_value(dst_main, dst_extras),
        "dstTypedText": _typed_text(dst_main, dst_mc),
        "dstFreeTypedText": "",
        "dstMC": dst_mc or "",
        "adults": str(params.adults),
        "children": str(params.children),
        "infants": str(params.infants),
        "minHourStay": params.min_hour_stay,
        "maxHourStay": params.max_hour_stay,
        "minHourOutbound": params.min_hour_outbound,
        "maxHourOutbound": params.max_hour_outbound,
        "minHourInbound": params.min_hour_inbound,
        "maxHourInbound": params.max_hour_inbound,
        "depdate": dep,
        "arrdate": arr,
        "minDaysStay": str(params.min_days_stay),
        "maxDaysStay": str(params.max_days_stay),
        "nextday": str(params.next_day),
        "autoprice": "true",
        "currency": params.currency,
        "wizzxclub": "false",
        "flyoneclub": "false",
        "blueairbenefits": "false",
        "megavolotea": "false",
        "schengen": "true" if params.schengen_only else "false",
        "transfer": "true" if (
            params.allow_transfer
            or (
                not params.is_oneway
                and dst_main != "XXX"
                and (not params.same_dep or not params.same_arr)
            )
        ) else "false",
        "samedep": "true" if params.same_dep else "false",
        "samearr": "true" if params.same_arr else "false",
        "maxChng": str(params.max_changes),
        "isOneway": "oneway" if params.is_oneway else "return",
        "lang": "en",
        "resultSubmit": "Search",
        **weekday_bits,
        **_extra_params("src", src_extras),
        **_extra_params("dst", dst_extras),
    }

    return f"{SEARCH_URL}?{urlencode(query)}"


async def fetch_search_results(params: SearchParams) -> str:
    url = build_search_url(params)
    async with httpx.AsyncClient(headers=HEADERS, timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


AIRPORTS_JS_URL = "https://static3.azair.us/www-azair-eu-assets/js/airports_array.js"


async def fetch_airports_js() -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30.0) as client:
        resp = await client.get(AIRPORTS_JS_URL)
        resp.raise_for_status()
        return resp.text


def _dedupe_results(results: list[FlightResult]) -> list[FlightResult]:
    seen = set()
    unique = []
    for result in results:
        key = (
            result.total_price,
            result.outbound_date,
            result.return_date,
            tuple(
                (s.departure_airport_code, s.departure_time, s.arrival_airport_code, s.arrival_time)
                for s in result.outbound_segments
            ),
            tuple(
                (s.departure_airport_code, s.departure_time, s.arrival_airport_code, s.arrival_time)
                for s in result.return_segments
            ),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


MAX_STAY_RETRIES = 3


async def _search_once(params: SearchParams) -> list[FlightResult]:
    return parse_results(await fetch_search_results(params))


async def search_flights(params: SearchParams) -> list[FlightResult]:
    """Search azair and work around its unreliable empty responses.

    azair occasionally answers a valid query with an empty/error page. Retry
    the same query once before giving up. It also sometimes returns no results
    when ``min_days_stay`` and ``max_days_stay`` span several lengths (e.g.
    1-3) even though shorter trips exist, so retry a bounded number of
    narrower stay ranges and merge whatever is found.
    """
    results = await _search_once(params)

    if not results:
        await asyncio.sleep(1)
        results = await _search_once(params)

    if (
        results
        or params.is_oneway
        or params.min_days_stay >= params.max_days_stay
    ):
        return _dedupe_results(results)

    # The initial request already covered max_days_stay; try the shorter
    # ranges. Keep the number of retries bounded so huge ranges cannot turn
    # into dozens of slow requests.
    candidates = list(range(params.min_days_stay, params.max_days_stay))
    if len(candidates) > MAX_STAY_RETRIES:
        step = len(candidates) / MAX_STAY_RETRIES
        candidates = sorted({candidates[int(i * step)] for i in range(MAX_STAY_RETRIES)})

    for max_stay in candidates:
        retry_params = params.model_copy(update={"max_days_stay": max_stay})
        retry_results = await _search_once(retry_params)
        if retry_results:
            results.extend(retry_results)

    return _dedupe_results(results)
