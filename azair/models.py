import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .metros import METRO_AIRPORTS


DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%Y")
TIME_RE = re.compile(r"^([01]?\d|2[0-4]):([0-5]\d)$")
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")


def _parse_date(value: str) -> date:
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Invalid date {value!r}; expected YYYY-MM-DD, DD.MM.YYYY, "
        "YYYY/MM/DD, or DD/MM/YYYY"
    )


def _normalize_airport(value: str, field_name: str) -> str:
    code = str(value or "").strip().upper()
    if not code:
        raise ValueError(f"{field_name} must not be empty")
    if code == "XXX" or code in METRO_AIRPORTS or AIRPORT_RE.match(code):
        return code
    raise ValueError(
        f"Invalid {field_name} {value!r}; use a 3-letter IATA code, XXX, "
        "or a metro/region code such as MIL_ALL"
    )


def _normalize_time(value: str, field_name: str) -> str:
    text = str(value).strip()
    match = TIME_RE.match(text)
    if not match:
        raise ValueError(f"Invalid {field_name} {value!r}; expected H:MM")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours == 24 and minutes != 0:
        raise ValueError(f"Invalid {field_name} {value!r}; 24:00 is the latest time")
    return f"{hours}:{minutes:02d}"


def _time_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


class FlightSegment(BaseModel):
    airline: str
    airline_iata: str
    flight_number: str
    departure_airport: str
    departure_airport_code: str
    departure_time: str
    arrival_airport: str
    arrival_airport_code: str
    arrival_time: str
    duration: str
    price: float
    currency: str


class FlightResult(BaseModel):
    total_price: float
    currency: str
    length_of_stay_days: int
    outbound_date: str
    return_date: str
    outbound_segments: list[FlightSegment]
    return_segments: list[FlightSegment]
    booking_url: str


class Airport(BaseModel):
    code: str
    name: str


class SearchParams(BaseModel):
    src_airport: str = Field(description="Source airport IATA code, e.g. PRG, WMI, STN. Metro/region codes such as MIL_ALL, PAR_ALL, IT or BALTIC are expanded automatically")
    dst_airport: str = Field(description="Destination IATA code, e.g. STN, XXX for anywhere in Europe, or a metro/region code such as MIL_ALL, PAR_ALL, IT, BALTIC")
    src_airports: Optional[list[str]] = Field(default=None, description="Additional source airports searched together with src_airport, e.g. BRQ, NUE alongside PRG")
    dst_airports: Optional[list[str]] = Field(default=None, description="Additional destination airports searched together with dst_airport, e.g. LIN, BGY alongside MXP")
    src_metro_code: Optional[str] = Field(default=None, description="Source metro/region code covering several airports, e.g. MIL_ALL (MXP, BGY, LIN), LON_ALL, IT; expanded automatically")
    dst_metro_code: Optional[str] = Field(default=None, description="Destination metro/region code covering several airports, e.g. MIL_ALL, PAR_ALL, LON_ALL, IT; expanded automatically")
    dep_date: str = Field(description="Earliest departure date, format DD.MM.YYYY or YYYY-MM-DD")
    arr_date: str = Field(description="Latest return date, format DD.MM.YYYY or YYYY-MM-DD")
    min_days_stay: int = Field(default=2, ge=0, le=60, description="Minimum trip length in nights between outbound and return flight (default 2)")
    max_days_stay: int = Field(default=7, ge=0, le=60, description="Maximum trip length in nights between outbound and return flight (default 7)")
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult travellers aged 12+ (default 1)")
    children: int = Field(default=0, ge=0, le=8, description="Number of children aged 2-11 (default 0)")
    infants: int = Field(default=0, ge=0, le=8, description="Number of infants under 2 years (default 0)")
    currency: str = Field(default="EUR", description="Currency for prices, e.g. EUR, USD, GBP, PLN, CZK (default EUR)")
    max_changes: int = Field(default=1, ge=0, le=3, description="Maximum stopovers per flight leg, 0 means direct flights only (default 1)")
    is_oneway: bool = Field(default=False, description="Search one-way flights only; false searches return flights (default false)")
    schengen_only: bool = Field(default=False, description="Only allow transfers within the Schengen area (default false)")
    allow_transfer: bool = Field(default=False, description="Allow ground transfer between different airports during a connection, e.g. arriving at one airport and departing from another. Automatically enabled when same_dep or same_arr is false (default false)")
    departure_weekdays: Optional[list[int]] = Field(default=None, description="Weekdays the outbound flight may depart on, 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun; omit for any day")
    return_weekdays: Optional[list[int]] = Field(default=None, description="Weekdays the return flight may depart on, 0=Mon..6=Sun; omit for any day")
    min_hour_outbound: str = Field(default="0:00", description="Earliest departure time of the outbound flight, 24h local time as H:MM (default 0:00)")
    max_hour_outbound: str = Field(default="24:00", description="Latest departure time of the outbound flight, 24h local time as H:MM (default 24:00)")
    min_hour_inbound: str = Field(default="0:00", description="Earliest departure time of the return flight, 24h local time as H:MM (default 0:00)")
    max_hour_inbound: str = Field(default="24:00", description="Latest departure time of the return flight, 24h local time as H:MM (default 24:00)")
    min_hour_stay: str = Field(default="0:45", description="Minimum stopover (layover) duration between connecting flights as H:MM (default 0:45); applies only to itineraries with changes")
    max_hour_stay: str = Field(default="23:20", description="Maximum stopover (layover) duration between connecting flights as H:MM (default 23:20); applies only to itineraries with changes")
    next_day: int = Field(default=0, ge=0, le=7, description="Allow waiting at the airport overnight so the next flight departs on the following day; 0 disallows overnight waits, up to 7 days (default 0)")
    same_dep: bool = Field(default=True, description="Require the return flight to arrive at the same airport the outbound flight departed from (default true)")
    same_arr: bool = Field(default=True, description="Require the return flight to depart from the same airport the outbound flight arrived at (default true)")

    @field_validator("src_airport", "dst_airport")
    @classmethod
    def _validate_airport(cls, value: str, info) -> str:
        return _normalize_airport(value, info.field_name)

    @field_validator("src_airports", "dst_airports")
    @classmethod
    def _normalize_airport_list(cls, value: Optional[list[str]], info) -> Optional[list[str]]:
        if value is None:
            return None
        result = []
        seen = set()
        for item in value:
            code = _normalize_airport(item, info.field_name)
            if code not in seen:
                seen.add(code)
                result.append(code)
        return result or None

    @field_validator("src_metro_code", "dst_metro_code")
    @classmethod
    def _normalize_metro_code(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return None
        code = value.strip().upper()
        if not code:
            return None
        if code not in METRO_AIRPORTS:
            raise ValueError(
                f"Invalid {info.field_name} {value!r}; use a metro/region code "
                "such as MIL_ALL, IT, or DE"
            )
        return code

    @field_validator("dep_date", "arr_date")
    @classmethod
    def _normalize_date(cls, value: str) -> str:
        return _parse_date(value).isoformat()

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        code = str(value or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", code):
            raise ValueError(f"Invalid currency {value!r}; expected a 3-letter code such as EUR")
        return code

    @field_validator("departure_weekdays", "return_weekdays")
    @classmethod
    def _normalize_weekdays(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        if value is None:
            return None
        days = sorted({int(day) for day in value})
        if any(day < 0 or day > 6 for day in days):
            raise ValueError("Weekdays must be in the range 0 (Monday) to 6 (Sunday)")
        return days or None

    @field_validator(
        "min_hour_outbound",
        "max_hour_outbound",
        "min_hour_inbound",
        "max_hour_inbound",
        "min_hour_stay",
        "max_hour_stay",
    )
    @classmethod
    def _validate_time(cls, value: str, info) -> str:
        return _normalize_time(value, info.field_name)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "SearchParams":
        if self.min_days_stay > self.max_days_stay:
            raise ValueError(
                f"min_days_stay ({self.min_days_stay}) must not be greater than "
                f"max_days_stay ({self.max_days_stay})"
            )
        dep = date.fromisoformat(self.dep_date)
        arr = date.fromisoformat(self.arr_date)
        if dep > arr:
            raise ValueError(
                f"dep_date ({self.dep_date}) must not be after arr_date ({self.arr_date})"
            )
        for field_name, minimum, maximum in (
            ("outbound", self.min_hour_outbound, self.max_hour_outbound),
            ("inbound", self.min_hour_inbound, self.max_hour_inbound),
            ("stay", self.min_hour_stay, self.max_hour_stay),
        ):
            if _time_minutes(minimum) > _time_minutes(maximum):
                raise ValueError(
                    f"min_hour_{field_name} ({minimum}) must not be after "
                    f"max_hour_{field_name} ({maximum})"
                )
        for prefix in ("src", "dst"):
            metro_code = getattr(self, f"{prefix}_metro_code")
            if not metro_code:
                continue
            airport = getattr(self, f"{prefix}_airport")
            ports = METRO_AIRPORTS[metro_code][1]
            if airport in METRO_AIRPORTS:
                if airport != metro_code:
                    raise ValueError(
                        f"{prefix}_airport ({airport}) conflicts with "
                        f"{prefix}_metro_code ({metro_code})"
                    )
            elif airport not in ports:
                raise ValueError(
                    f"{prefix}_airport ({airport}) is not part of "
                    f"{prefix}_metro_code ({metro_code})"
                )
        return self
