"""
FastAPI router for trip aggregation endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from decimal import Decimal
from app.schemas.booking import (
    TripResponse,
    TripsListResponse,
    BookingResponse,
    CreateTripRequest,
    TripPreviewResponse,
    TripCitySuggestion,
)
from app.routers.cities import _city_data_to_response, _create_city_id, _geocode_city, _store_city
from app.models.booking import City, Visit
from app.services.dynamodb_service import DynamoDBService
from app.functions.common import normalize_booking_data
import logfire

router = APIRouter(prefix="/trips", tags=["trips"])
db_service = DynamoDBService()


def _match_bookings_to_city(city_name: str, all_bookings: list) -> list:
    """Find bookings whose city field matches (case-insensitive)."""
    name_lower = city_name.lower()
    return [
        b for b in all_bookings
        if (b.get("city") or "").lower() == name_lower
    ]


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

        start_dates = []
        end_dates = []
        for city in cities:
            for visit in (city.get("visits") or []):
                if visit.get("trip") == trip_name:
                    start_dates.append(visit.get("start_date", ""))
                    end_dates.append(visit.get("end_date", ""))

        booking_responses = []
        filtered_starts = [d for d in start_dates if d]
        filtered_ends = [d for d in end_dates if d]
        if filtered_starts and filtered_ends:
            min_start = min(filtered_starts)
            max_end = max(filtered_ends)
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


@router.post("/preview", response_model=TripPreviewResponse)
async def preview_trip(request: CreateTripRequest):
    """
    Preview a trip before creating it. For each city, auto-suggests visit dates
    by matching bookings whose city field matches the city name.
    """
    with logfire.span("preview_trip", trip_name=request.trip_name):
        all_bookings = db_service.get_all_bookings()
        suggestions = []

        for city_input in request.cities:
            city_id = _create_city_id(city_input.city_name, city_input.country, city_input.state)
            existing = db_service.get_booking_by_id(city_id)

            matched = _match_bookings_to_city(city_input.city_name, all_bookings)
            matched.sort(key=lambda b: b.get("check_in_date", ""))

            suggested_start = None
            suggested_end = None
            if matched:
                suggested_start = min(b.get("check_in_date", "") for b in matched if b.get("check_in_date"))
                suggested_end = max(b.get("check_out_date", "") for b in matched if b.get("check_out_date"))

            suggestions.append(TripCitySuggestion(
                city_name=city_input.city_name,
                country=city_input.country,
                state=city_input.state,
                city_id=city_id if existing else None,
                city_exists=existing is not None,
                suggested_start_date=city_input.start_date or suggested_start,
                suggested_end_date=city_input.end_date or suggested_end,
                matched_bookings=[BookingResponse(**b) for b in matched],
            ))

        return TripPreviewResponse(
            trip_name=request.trip_name,
            cities=suggestions,
        )


@router.post("/create", response_model=TripResponse)
async def create_trip(request: CreateTripRequest):
    """
    Create a trip by creating cities (if needed) and adding visits.
    Dates are auto-assigned from matching bookings if not provided.
    """
    with logfire.span("create_trip", trip_name=request.trip_name):
        all_bookings = db_service.get_all_bookings()
        import os

        for city_input in request.cities:
            city_id = _create_city_id(city_input.city_name, city_input.country, city_input.state)
            existing = db_service.get_booking_by_id(city_id)

            # Determine dates
            start_date = city_input.start_date
            end_date = city_input.end_date

            if not start_date or not end_date:
                matched = _match_bookings_to_city(city_input.city_name, all_bookings)
                if matched:
                    if not start_date:
                        start_date = min(b.get("check_in_date", "") for b in matched if b.get("check_in_date"))
                    if not end_date:
                        end_date = max(b.get("check_out_date", "") for b in matched if b.get("check_out_date"))

            if existing:
                # City exists — add visit
                visits = []
                for v in (existing.get("visits") or []):
                    if isinstance(v, dict):
                        visits.append(Visit(**v))

                normalized = normalize_booking_data(existing, City)
                city = City.model_construct(**normalized)
                city.visits = visits or []

                # Always add a new visit (allows multiple visits per trip per city)
                city.visits.append(Visit(
                    start_date=start_date,
                    end_date=end_date,
                    trip=request.trip_name,
                ))
                _store_city(city, city_id)
            else:
                # Create new city
                city_data = {
                    "city_id": city_id,
                    "city_name": city_input.city_name,
                    "country": city_input.country,
                    "state": city_input.state,
                    "visits": [Visit(
                        start_date=start_date,
                        end_date=end_date,
                        trip=request.trip_name,
                    )],
                }

                geocode_result = _geocode_city(city_input.city_name, city_input.country, city_input.state)
                if geocode_result:
                    city_data["latitude"] = Decimal(str(geocode_result["latitude"]))
                    city_data["longitude"] = Decimal(str(geocode_result["longitude"]))
                    city_data["location_name"] = geocode_result.get("location", "")

                city = City(**city_data)
                _store_city(city, city_id)

        # Return the full trip — use direct query since cities may not have dates yet
        cities = db_service.get_cities_by_trip(request.trip_name)
        city_responses = [_city_data_to_response(c) for c in cities]
        return TripResponse(
            trip_name=request.trip_name,
            cities=city_responses,
            bookings=[],
        )


def _cluster_bookings(bookings: list) -> list:
    """
    Group bookings into clusters where check-out of one overlaps or is adjacent
    to check-in of the next. Returns list of (start_date, end_date) tuples.
    """
    dated = []
    for b in bookings:
        start = b.get("check_in_date", "")
        end = b.get("check_out_date", "")
        if start and end:
            dated.append((start, end))
    if not dated:
        return []

    dated.sort(key=lambda x: x[0])
    clusters = [list(dated[0])]
    for start, end in dated[1:]:
        # If this booking starts on or before the current cluster ends, merge
        if start <= clusters[-1][1]:
            clusters[-1][1] = max(clusters[-1][1], end)
        else:
            clusters.append([start, end])

    return [(c[0], c[1]) for c in clusters]


@router.post("/{trip_name}/auto-assign", response_model=TripResponse)
async def auto_assign_dates(trip_name: str):
    """
    Auto-assign visit dates for a trip by matching bookings to cities by name.
    Creates one visit per booking cluster (non-contiguous date ranges become separate visits).
    Existing visits with dates are preserved.
    """
    with logfire.span("auto_assign_dates", trip_name=trip_name):
        cities = db_service.get_cities_by_trip(trip_name)
        if not cities:
            raise HTTPException(status_code=404, detail=f"No cities found for trip: {trip_name}")

        all_bookings = db_service.get_all_bookings()
        updated_count = 0

        for city_data in cities:
            city_name = city_data.get("city_name", "")
            city_id = city_data.get("city_id", city_data.get("confirmation", ""))

            visits = []
            for v in (city_data.get("visits") or []):
                visit = Visit(**v) if isinstance(v, dict) else v
                visits.append(visit)

            # Find all visits for this trip (there may be multiple)
            trip_visits = [(i, v) for i, v in enumerate(visits) if v.trip == trip_name]
            if not trip_visits:
                continue

            # Match bookings by city name
            matched = _match_bookings_to_city(city_name, all_bookings)
            if not matched:
                continue

            clusters = _cluster_bookings(matched)
            if not clusters:
                continue

            # Count how many visits already have dates
            dated_visits = [(i, v) for i, v in trip_visits if v.start_date and v.end_date]
            dateless_visits = [(i, v) for i, v in trip_visits if not v.start_date or not v.end_date]

            # Exclude clusters that are already covered by existing dated visits
            uncovered_clusters = []
            for c_start, c_end in clusters:
                already_covered = any(
                    v.start_date == c_start and v.end_date == c_end
                    for _, v in dated_visits
                )
                if not already_covered:
                    uncovered_clusters.append((c_start, c_end))

            if not uncovered_clusters:
                continue

            # Assign uncovered clusters: fill dateless visits first, then add new ones
            changed = False
            for c_start, c_end in uncovered_clusters:
                if dateless_visits:
                    idx, visit = dateless_visits.pop(0)
                    visit.start_date = c_start
                    visit.end_date = c_end
                    changed = True
                else:
                    visits.append(Visit(start_date=c_start, end_date=c_end, trip=trip_name))
                    changed = True

            if changed:
                normalized = normalize_booking_data(city_data, City)
                city = City.model_construct(**normalized)
                city.visits = visits
                _store_city(city, city_id)
                updated_count += 1

        logfire.info("auto_assign_dates complete", trip_name=trip_name, updated=updated_count)
        return await get_trip(trip_name)
