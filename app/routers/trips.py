"""
FastAPI router for trip aggregation endpoints.
"""
from fastapi import APIRouter, HTTPException
from app.schemas.booking import (
    TripResponse,
    TripsListResponse,
    BookingResponse,
)
from app.routers.cities import _city_data_to_response
from app.services.dynamodb_service import DynamoDBService
import logfire

router = APIRouter(prefix="/trips", tags=["trips"])
db_service = DynamoDBService()


@router.get("/", response_model=TripsListResponse)
async def list_trips():
    """List all unique trip names."""
    with logfire.span("list_trips"):
        trip_names = db_service.get_all_trip_names()
        return TripsListResponse(trips=trip_names, count=len(trip_names))


@router.get("/{trip_name}", response_model=TripResponse)
async def get_trip(trip_name: str):
    """Get aggregated trip data: cities with their visits and bookings within the trip date range."""
    with logfire.span("get_trip", trip_name=trip_name):
        cities = db_service.get_cities_by_trip(trip_name)
        if not cities:
            raise HTTPException(status_code=404, detail=f"No cities found for trip: {trip_name}")

        city_responses = [_city_data_to_response(c) for c in cities]

        # Find the overall trip date range from city visits
        start_dates = []
        end_dates = []
        for city in cities:
            for visit in (city.get("visits") or []):
                if visit.get("trip") == trip_name:
                    start_dates.append(visit.get("start_date", ""))
                    end_dates.append(visit.get("end_date", ""))

        # Get bookings within the trip date range
        booking_responses = []
        if start_dates and end_dates:
            min_start = min(d for d in start_dates if d)
            max_end = max(d for d in end_dates if d)
            if min_start and max_end:
                bookings = db_service.get_bookings_by_date_range(
                    start_date=min_start,
                    end_date=max_end,
                    date_field="check_in_date",
                )
                booking_responses = [BookingResponse(**b) for b in bookings]

        return TripResponse(
            trip_name=trip_name,
            cities=city_responses,
            bookings=booking_responses,
        )
