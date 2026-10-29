from pydantic import BaseModel, Field
from typing import Optional


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
    min_days_stay: int = Field(default=2, ge=0, le=30, description="Minimum trip length in nights between outbound and return flight (default 2)")
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
