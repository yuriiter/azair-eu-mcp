from bs4 import BeautifulSoup, Tag, NavigableString
import re
from .models import FlightResult, FlightSegment


PRICE_RE = re.compile(r"[€$£złFtKčkrруб₴р.₪¥]\s*([\d.]+)")
DAYS_RE = re.compile(r"(\d+)\s*days")


def _parse_price(text: str) -> float:
    m = PRICE_RE.search(text)
    return float(m.group(1)) if m else 0.0


def _extract_currency(text: str) -> str:
    symbols = {"€": "EUR", "$": "USD", "£": "GBP", "Kč": "CZK", "kr": "DKK",
               "zł": "PLN", "Ft": "HUF", "руб": "RUB", "₴": "UAH", "р.": "BYN", "₪": "ILS", "¥": "JPY"}
    for sym, cur in symbols.items():
        if sym in text:
            return cur
    return "EUR"


def _text_before_code(span: Tag) -> str:
    parts = []
    for child in span.children:
        if isinstance(child, NavigableString):
            t = str(child).strip().replace("\u00a0", " ")
            if t:
                parts.append(t)
        elif isinstance(child, Tag) and child.get("class") == ["code"]:
            break
    return " ".join(parts)


def _parse_segments_from_detail(detail_div: Tag, currency: str) -> list[FlightSegment]:
    segments = []
    for p in detail_div.find_all("p", recursive=False):
        from_span = p.find("span", class_="from")
        to_span = p.find("span", class_="to")
        airline_span = p.find("span", class_="airline")
        leg_price_span = p.find("span", class_="legPrice")

        if not (from_span and to_span):
            continue

        dep_code_span = from_span.find("span", class_="code")
        arr_code_span = to_span.find("span", class_="code")

        dep_code = dep_code_span.get_text(strip=True)[:3] if dep_code_span else ""
        arr_code = arr_code_span.get_text(strip=True)[:3] if arr_code_span else ""

        from_text = _text_before_code(from_span)
        to_text = _text_before_code(to_span)

        from_tokens = [t for t in from_text.split() if t]
        dep_time = from_tokens[1] if len(from_tokens) > 1 else ""
        dep_airport = " ".join(from_tokens[2:]) if len(from_tokens) > 2 else ""

        to_tokens = [t for t in to_text.split() if t]
        arr_time = to_tokens[0] if to_tokens else ""
        arr_airport = " ".join(to_tokens[1:]) if len(to_tokens) > 1 else ""

        airline = airline_span.get_text(strip=True) if airline_span else ""
        airline_iata = ""
        if airline_span and isinstance(airline_span, Tag):
            for cls in airline_span.get("class", []):
                if cls.startswith("iata"):
                    airline_iata = cls[4:]
                    break

        flight_number = ""
        flight_link = to_span.find("a") if to_span else None
        if flight_link:
            flight_number = flight_link.get_text(strip=True)

        leg_price = _parse_price(leg_price_span.get_text(" ")) if leg_price_span else 0.0

        segments.append(FlightSegment(
            airline=airline,
            airline_iata=airline_iata,
            flight_number=flight_number,
            departure_airport=dep_airport,
            departure_airport_code=dep_code,
            departure_time=dep_time,
            arrival_airport=arr_airport,
            arrival_airport_code=arr_code,
            arrival_time=arr_time,
            duration="",
            price=leg_price,
            currency=currency,
        ))
    return segments


def parse_results(html: str) -> list[FlightResult]:
    soup = BeautifulSoup(html, "lxml")
    reslist = soup.find(id="reslist")
    if not reslist:
        return []

    results = []
    for result_div in reslist.find_all("div", class_="result", recursive=False):
        text_div = result_div.find("div", class_="text")
        if not text_div:
            continue

        total_price_span = text_div.find("span", class_="sumPrice")
        if not total_price_span:
            continue

        total_text = total_price_span.get_text(" ")
        currency = _extract_currency(total_text)
        total_price = _parse_price(total_text)

        length_span = text_div.find("span", class_="lengthOfStay")
        length_of_stay = 0
        if length_span:
            m = DAYS_RE.search(length_span.get_text(strip=True))
            if m:
                length_of_stay = int(m.group(1))

        summary_ps = text_div.find_all("p", recursive=False)
        direction_ps = [p for p in summary_ps if p.find("span", class_="caption")
                        and p.find("span", class_="caption").get_text(strip=True) in ("There", "Back")]

        detail_divs = text_div.find_all("div", class_="detail", recursive=False)

        booking_url = ""
        if detail_divs:
            book_link = detail_divs[0].find("a", class_="affPopUp", href=True)
            if book_link:
                booking_url = book_link["href"]

        outbound_date = ""
        return_date = ""
        outbound_duration = ""
        return_duration = ""

        for p in direction_ps:
            caption = p.find("span", class_="caption").get_text(strip=True)
            date_span = p.find("span", class_="date")
            durcha_span = p.find("span", class_="durcha")
            date = date_span.get_text(strip=True) if date_span else ""
            duration = durcha_span.get_text(strip=True) if durcha_span else ""
            if caption == "There":
                outbound_date = date
                outbound_duration = duration
            elif caption == "Back":
                return_date = date
                return_duration = duration

        outbound_segments: list[FlightSegment] = []
        return_segments: list[FlightSegment] = []

        for i, div in enumerate(detail_divs[:2]):
            segs = _parse_segments_from_detail(div, currency)
            for seg in segs:
                duration = outbound_duration if i == 0 else return_duration
                if not seg.duration:
                    seg.duration = duration
            if i == 0:
                outbound_segments = segs
            else:
                return_segments = segs

        results.append(FlightResult(
            total_price=total_price,
            currency=currency,
            length_of_stay_days=length_of_stay,
            outbound_date=outbound_date,
            return_date=return_date,
            outbound_segments=outbound_segments,
            return_segments=return_segments,
            booking_url=booking_url,
        ))

    return results
