"""
FastAPI router for booking endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.schemas.booking import BookingResponse, BookingUpdateRequest, BookingsListResponse
from app.services.dynamodb_service import DynamoDBService
from app.functions.common import store_result
from pydantic import BaseModel
import os
import logfire

router = APIRouter(prefix="/bookings", tags=["bookings"])
db_service = DynamoDBService()


@router.get("/{confirmation}", response_model=BookingResponse)
async def get_booking_by_id(confirmation: str):
    """
    Get a booking by confirmation ID.
    
    Args:
        confirmation: The booking confirmation ID
        
    Returns:
        Booking details
    """
    with logfire.span("get_booking_by_id", confirmation=confirmation):
        booking = db_service.get_booking_by_id(confirmation)
        
        if not booking:
            raise HTTPException(
                status_code=404,
                detail=f"Booking with confirmation '{confirmation}' not found"
            )
        
        return BookingResponse(**booking)


@router.get("/", response_model=BookingsListResponse)
async def get_bookings_by_date_range(
    start_date: Optional[str] = Query(
        None,
        description="Start date for filtering (ISO format: YYYY-MM-DD or full date string)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date for filtering (ISO format: YYYY-MM-DD or full date string)",
    ),
    date_field: str = Query(
        "check_in_date",
        description="Date field to filter on (check_in_date, check_out_date, booking_date, created_at)",
    )
):
    """
    Get bookings within a date range.
    
    If no dates are provided, returns all bookings (use with caution on large tables).
    
    Args:
        start_date: Start date for filtering
        end_date: End date for filtering
        date_field: Field to filter on (check_in_date, check_out_date, booking_date, created_at)
        
    Returns:
        List of bookings matching the date range
    """
    with logfire.span(
        "get_bookings_by_date_range",
        start_date=start_date,
        end_date=end_date,
        date_field=date_field
    ):
        bookings = db_service.get_bookings_by_date_range(
            start_date=start_date,
            end_date=end_date,
            date_field=date_field
        )
        
        # Convert to response models
        booking_responses = [BookingResponse(**booking) for booking in bookings]
        
        return BookingsListResponse(
            bookings=booking_responses,
            count=len(booking_responses)
        )


class BookingForStorage(BaseModel):
    """Booking fields for DynamoDB storage. All optional for partial updates."""
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


@router.put("/{confirmation}", response_model=BookingResponse)
async def update_booking(confirmation: str, body: BookingUpdateRequest):
    """Update a booking by confirmation ID. Only provided fields are updated."""
    with logfire.span("update_booking", confirmation=confirmation):
        existing = db_service.get_booking_by_id(confirmation)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Booking with confirmation '{confirmation}' not found",
            )

        # Merge provided fields into existing data
        updates = body.model_dump(exclude_unset=True)
        merged = {**existing, **updates, "confirmation": confirmation}

        storage = BookingForStorage(**{
            k: v for k, v in merged.items()
            if k in BookingForStorage.model_fields
        })
        table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
        store_result(storage, table_name, {"confirmation": confirmation})

        updated = db_service.get_booking_by_id(confirmation)
        return BookingResponse(**updated)

