"""
Pydantic schemas for booking API responses.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class BookingResponse(BaseModel):
    """Booking response schema with all fields from DynamoDB."""
    confirmation: str
    name: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    early_check_in_time: Optional[str] = None
    early_check_in_cost: Optional[str] = None
    breakfast_included: Optional[bool] = None
    cancellation_terms: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    booking_date: Optional[str] = None
    what3words: Optional[str] = None
    website: Optional[str] = None
    amount_paid: Optional[str] = None
    amount_total: Optional[str] = None
    room_type: Optional[str] = None
    source_bucket: Optional[str] = None
    source_key: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BookingsListResponse(BaseModel):
    """Response schema for list of bookings."""
    bookings: list[BookingResponse]
    count: int

