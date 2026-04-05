import decimal
from datetime import date
from pydantic import BaseModel, HttpUrl
from typing import Optional, List


class Booking(BaseModel):
    guest_name: str
    provider_name: str
    confirmation: str
    booking_type: Optional[str] = "hotel"  # "hotel", "train", "flight", "car", "tour", "other"
    check_in_date: str
    check_out_date: str
    check_in_time: str
    check_out_time: str
    early_check_in_time: str
    early_check_in_cost: str
    breakfast_included: bool
    cancellation_terms: str
    street_address: str
    city: str
    departure_city: Optional[str] = ""     # For transit: city of departure
    arrival_city: Optional[str] = ""      # For transit: city of arrival
    departure_station: Optional[str] = "" # For transit: station/airport name (e.g., "Kings Cross", "LHR T5")
    arrival_station: Optional[str] = ""   # For transit: station/airport name
    route_number: Optional[str] = ""      # Flight/train number (e.g., "BA123", "LNER 12:30")
    seat_class: Optional[str] = ""        # e.g., "Standard Class", "Business"
    seat_number: Optional[str] = ""       # e.g., "42A", "Coach C Seat 14"
    postal_code: str
    booking_date: str
    what3words: str
    website: HttpUrl
    amount_paid: str
    amount_total: str
    room_type: str


class BookingWithMeta(Booking):
    source_key: str


class FullBookingTable(BookingWithMeta):
    latitude: decimal.Decimal
    longitude: decimal.Decimal


class ExtractionResult(BaseModel):
    kind: str
    booking: Optional[Booking]


class Visit(BaseModel):
    """A visit to a city as part of a trip."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    trip: str


class City(BaseModel):
    """City entry with geocoded location and visits."""
    city_name: str
    country: str
    state: Optional[str] = None
    latitude: Optional[decimal.Decimal] = None
    longitude: Optional[decimal.Decimal] = None
    location_name: Optional[str] = None  # Full formatted address from geocoding
    visits: Optional[List[Visit]] = []
    # Use city name + country (+ state if provided) as unique identifier
    city_id: str  # Format: "city_name,country" or "city_name,state,country"


def get_extract_booking_tool():
    """Return tool definition in Anthropic/Claude format."""
    return {
        "name": "extract_booking",
        "description": "Extracts booking information from an email.",
        "input_schema": ExtractionResult.model_json_schema(),
    }