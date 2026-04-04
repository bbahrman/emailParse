"""
FastAPI router for city endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from decimal import Decimal
from app.models.booking import City, Visit
from app.schemas.booking import CityResponse, CitiesListResponse, VisitResponse
from app.services.dynamodb_service import DynamoDBService
from app.functions.common import store_result, normalize_booking_data
from app.functions.geocoding import geocode_address
import os
import logfire

router = APIRouter(prefix="/cities", tags=["cities"])
db_service = DynamoDBService()


def _create_city_id(city_name: str, country: str, state: Optional[str] = None) -> str:
    if state:
        return f"{city_name},{state},{country}".lower().strip()
    return f"{city_name},{country}".lower().strip()


def _geocode_city(city_name: str, country: str, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
    address_parts = [city_name]
    if state:
        address_parts.append(state)
    address_parts.append(country)
    return geocode_address(", ".join(address_parts))


def _city_data_to_response(city_data: Dict[str, Any]) -> CityResponse:
    visits = []
    for visit in (city_data.get("visits") or []):
        if isinstance(visit, dict):
            visits.append(VisitResponse(**visit))
        elif isinstance(visit, Visit):
            visits.append(VisitResponse(**visit.model_dump()))

    return CityResponse(
        city_id=city_data.get("city_id", city_data.get("confirmation", "")),
        city_name=city_data.get("city_name", ""),
        country=city_data.get("country", ""),
        state=city_data.get("state"),
        latitude=str(city_data["latitude"]) if city_data.get("latitude") else None,
        longitude=str(city_data["longitude"]) if city_data.get("longitude") else None,
        location_name=city_data.get("location_name"),
        visits=visits,
    )


def _store_city(city: City, city_id: str):
    """Store a city in DynamoDB."""
    from app.functions.api_city import CityForStorage
    city_dict = city.model_dump(mode="json")
    if city_dict.get("visits"):
        city_dict["visits"] = [
            v.model_dump(mode="json") if isinstance(v, Visit) else v
            for v in city_dict["visits"]
        ]
    city_storage = CityForStorage(**city_dict)
    table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
    store_result(city_storage, table_name, {"confirmation": city_id})


@router.get("/", response_model=CitiesListResponse)
async def list_cities(
    trip: Optional[str] = Query(None, description="Filter by trip name"),
):
    """List all cities, optionally filtered by trip name."""
    with logfire.span("list_cities", trip=trip):
        if trip:
            cities = db_service.get_cities_by_trip(trip)
        else:
            cities = db_service.get_all_cities()

        city_responses = [_city_data_to_response(c) for c in cities]
        return CitiesListResponse(cities=city_responses, count=len(city_responses))


@router.get("/{city_id}", response_model=CityResponse)
async def get_city(city_id: str):
    """Get a city by its ID."""
    with logfire.span("get_city", city_id=city_id):
        city_data = db_service.get_booking_by_id(city_id)
        if not city_data:
            raise HTTPException(status_code=404, detail=f"City not found: {city_id}")
        return _city_data_to_response(city_data)


@router.post("/", response_model=CityResponse, status_code=201)
async def create_city(
    city_name: str = Query(..., description="City name"),
    country: str = Query(..., description="Country"),
    state: Optional[str] = Query(None, description="State/province"),
):
    """Create a new city entry with geocoding."""
    with logfire.span("create_city", city_name=city_name, country=country):
        city_id = _create_city_id(city_name, country, state)

        existing = db_service.get_booking_by_id(city_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"City already exists: {city_id}")

        city_data = {
            "city_id": city_id,
            "city_name": city_name,
            "country": country,
            "state": state,
            "visits": [],
        }

        geocode_result = _geocode_city(city_name, country, state)
        if geocode_result:
            city_data["latitude"] = Decimal(str(geocode_result["latitude"]))
            city_data["longitude"] = Decimal(str(geocode_result["longitude"]))
            city_data["location_name"] = geocode_result.get("location", "")

        city = City(**city_data)
        _store_city(city, city_id)
        return _city_data_to_response(city.model_dump(mode="json"))


@router.put("/{city_id}", response_model=CityResponse)
async def update_city(
    city_id: str,
    city_name: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
    """Update a city's location info. Re-geocodes if location fields change."""
    with logfire.span("update_city", city_id=city_id):
        city_data = db_service.get_booking_by_id(city_id)
        if not city_data:
            raise HTTPException(status_code=404, detail=f"City not found: {city_id}")

        # Rebuild visits as Visit objects
        visits = []
        for v in (city_data.get("visits") or []):
            if isinstance(v, dict):
                visits.append(Visit(**v))
            else:
                visits.append(v)

        normalized = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized)
        city.visits = visits

        changed = False
        if city_name:
            city.city_name = city_name
            changed = True
        if country:
            city.country = country
            changed = True
        if state is not None:
            city.state = state
            changed = True

        if changed:
            geocode_result = _geocode_city(city.city_name, city.country, city.state)
            if geocode_result:
                city.latitude = Decimal(str(geocode_result["latitude"]))
                city.longitude = Decimal(str(geocode_result["longitude"]))
                city.location_name = geocode_result.get("location", "")

        _store_city(city, city_id)
        return _city_data_to_response(city.model_dump(mode="json"))


@router.post("/{city_id}/visits", response_model=CityResponse)
async def add_visit(
    city_id: str,
    start_date: str = Query(..., description="Visit start date"),
    end_date: str = Query(..., description="Visit end date"),
    trip: str = Query(..., description="Trip name"),
):
    """Add a visit to an existing city."""
    with logfire.span("add_visit", city_id=city_id):
        city_data = db_service.get_booking_by_id(city_id)
        if not city_data:
            raise HTTPException(status_code=404, detail=f"City not found: {city_id}")

        visits = []
        for v in (city_data.get("visits") or []):
            if isinstance(v, dict):
                visits.append(Visit(**v))
            else:
                visits.append(v)

        normalized = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized)
        city.visits = visits or []

        new_visit = Visit(start_date=start_date, end_date=end_date, trip=trip)
        city.visits.append(new_visit)

        _store_city(city, city_id)
        return _city_data_to_response(city.model_dump(mode="json"))


@router.put("/{city_id}/visits", response_model=CityResponse)
async def update_visit(
    city_id: str,
    trip: str = Query(..., description="Trip name to identify the visit"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    new_trip: Optional[str] = Query(None, description="New trip name"),
):
    """Update a specific visit in a city by trip name."""
    with logfire.span("update_visit", city_id=city_id, trip=trip):
        city_data = db_service.get_booking_by_id(city_id)
        if not city_data:
            raise HTTPException(status_code=404, detail=f"City not found: {city_id}")

        visits = []
        for v in (city_data.get("visits") or []):
            if isinstance(v, dict):
                visits.append(Visit(**v))
            else:
                visits.append(v)

        normalized = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized)
        city.visits = visits

        found = False
        for visit in city.visits:
            if visit.trip == trip:
                if start_date:
                    visit.start_date = start_date
                if end_date:
                    visit.end_date = end_date
                if new_trip:
                    visit.trip = new_trip
                found = True
                break

        if not found:
            raise HTTPException(
                status_code=404,
                detail=f'Visit with trip "{trip}" not found in city: {city_id}',
            )

        _store_city(city, city_id)
        return _city_data_to_response(city.model_dump(mode="json"))
