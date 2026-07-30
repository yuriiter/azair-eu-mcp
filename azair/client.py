import httpx
import re
from urllib.parse import urlencode
from .models import SearchParams


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


def _weekday_bit(weekdays: list[int] | None) -> dict[str, str]:
    bits = {}
    if weekdays is None:
        for i in range(7):
            bits[f"dep{i}"] = "true"
            bits[f"arr{i}"] = "true"
    else:
        for i in range(7):
            bits[f"dep{i}"] = "true" if i in weekdays else "false"
        for i in range(7):
            bits[f"arr{i}"] = "true" if i in weekdays else "false"
    return bits


def build_search_url(params: SearchParams) -> str:
    dep = _normalize_date(params.dep_date)
    arr = _normalize_date(params.arr_date)
    weekday_bits = _weekday_bit(params.departure_weekdays)

    query = {
        "searchtype": "flexi",
        "tp": "0",
        "srcAirport": f" [{params.src_airport}]",
        "srcTypedText": params.src_airport.lower()[:3],
        "srcFreeTypedText": "",
        "srcMC": "",
        "srcFreeAirport": "",
        "dstAirport": f" [{params.dst_airport}]",
        "dstTypedText": "anyw" if params.dst_airport == "XXX" else params.dst_airport.lower()[:3],
        "dstFreeTypedText": "",
        "dstMC": "",
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
        "transfer": "true" if params.allow_transfer else "false",
        "samedep": "true" if params.same_dep else "false",
        "samearr": "true" if params.same_arr else "false",
        "maxChng": str(params.max_changes),
        "isOneway": "oneway" if params.is_oneway else "return",
        "resultSubmit": "Search",
        **weekday_bits,
    }

    return f"{SEARCH_URL}?{urlencode(query)}"


async def fetch_search_results(params: SearchParams) -> str:
    url = build_search_url(params)
    async with httpx.AsyncClient(verify=False, headers=HEADERS, timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


AIRPORTS_JS_URL = "https://static3.azair.us/www-azair-eu-assets/js/airports_array.js"


async def fetch_airports_js() -> str:
    async with httpx.AsyncClient(verify=False, headers=HEADERS, timeout=30.0) as client:
        resp = await client.get(AIRPORTS_JS_URL)
        resp.raise_for_status()
        return resp.text
