"""
FastAPI router for booking endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.schemas.booking import BookingResponse, BookingsListResponse
from app.services.dynamodb_service import DynamoDBService
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
        example="2025-11-17"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date for filtering (ISO format: YYYY-MM-DD or full date string)",
        example="2025-11-20"
    ),
    date_field: str = Query(
        "check_in_date",
        description="Date field to filter on (check_in_date, check_out_date, booking_date, created_at)",
        example="check_in_date"
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

