"""
Pydantic schemas for API responses.
"""
from pydantic import BaseModel
from typing import Optional, List


class BookingResponse(BaseModel):
    """Booking response schema with all fields from DynamoDB."""
    confirmation: str
    guest_name: Optional[str] = None
    provider_name: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    early_check_in_time: Optional[str] = None
    early_check_in_cost: Optional[str] = None
    breakfast_included: Optional[bool] = None
    cancellation_terms: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    booking_date: Optional[str] = None
    what3words: Optional[str] = None
    website: Optional[str] = None
    amount_paid: Optional[str] = None
    amount_total: Optional[str] = None
    room_type: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    source_key: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BookingsListResponse(BaseModel):
    """Response schema for list of bookings."""
    bookings: list[BookingResponse]
    count: int


class VisitResponse(BaseModel):
    """Visit response schema."""
    start_date: str
    end_date: str
    trip: str


class CityResponse(BaseModel):
    """City response schema."""
    city_id: str
    city_name: str
    country: str
    state: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    location_name: Optional[str] = None
    visits: Optional[List[VisitResponse]] = []

    class Config:
        from_attributes = True


class CitiesListResponse(BaseModel):
    """Response schema for list of cities."""
    cities: list[CityResponse]
    count: int


class TripResponse(BaseModel):
    """Aggregated trip response with cities and bookings."""
    trip_name: str
    cities: List[CityResponse]
    bookings: List[BookingResponse]


class TripsListResponse(BaseModel):
    """Response schema for list of trips."""
    trips: List[str]
    count: int


class ObsidianBookingNote(BaseModel):
    """A booking formatted as an Obsidian markdown note."""
    filename: str
    content: str


class ObsidianTripExport(BaseModel):
    """Full trip export for Obsidian with overview and individual notes."""
    trip_name: str
    overview: str
    booking_notes: List[ObsidianBookingNote]
    city_notes: List[ObsidianBookingNote]


class ObsidianTripNote(BaseModel):
    """A single consolidated trip note for Obsidian sync."""
    trip_name: str
    filename: str
    content: str

