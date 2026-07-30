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
    src_airport: str = Field(description="Source airport IATA code")
    dst_airport: str = Field(description="Destination IATA code (XXX for anywhere)")
    dep_date: str = Field(description="Earliest departure date, DD.MM.YYYY or YYYY-MM-DD")
    arr_date: str = Field(description="Latest return date, DD.MM.YYYY or YYYY-MM-DD")
    min_days_stay: int = Field(default=2, ge=0, le=30)
    max_days_stay: int = Field(default=7, ge=0, le=60)
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=8)
    infants: int = Field(default=0, ge=0, le=8)
    currency: str = Field(default="EUR")
    max_changes: int = Field(default=1, ge=1, le=3)
    is_oneway: bool = Field(default=False)
    schengen_only: bool = Field(default=False)
    allow_transfer: bool = Field(default=False)
    departure_weekdays: Optional[list[int]] = Field(default=None, description="0=Mon..6=Sun")
    return_weekdays: Optional[list[int]] = Field(default=None)
    min_hour_outbound: str = Field(default="0:00")
    max_hour_outbound: str = Field(default="24:00")
    min_hour_inbound: str = Field(default="0:00")
    max_hour_inbound: str = Field(default="24:00")
    min_hour_stay: str = Field(default="0:45")
    max_hour_stay: str = Field(default="23:20")
    next_day: int = Field(default=0, ge=0, le=7)
    same_dep: bool = Field(default=True)
    same_arr: bool = Field(default=True)
