"""
FastAPI router for Obsidian export endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import Optional
from app.schemas.booking import ObsidianTripExport, ObsidianBookingNote, BookingResponse
from app.routers.cities import _city_data_to_response
from app.services.dynamodb_service import DynamoDBService
import logfire

router = APIRouter(prefix="/export", tags=["export"])
db_service = DynamoDBService()


def _booking_to_markdown(booking: dict) -> ObsidianBookingNote:
    """Convert a booking dict to an Obsidian-compatible markdown note."""
    confirmation = booking.get("confirmation", "unknown")
    provider = booking.get("provider_name", "Unknown Provider")
    city = booking.get("city", "")
    check_in = booking.get("check_in_date", "")
    check_out = booking.get("check_out_date", "")

    frontmatter_fields = {
        "type": "booking",
        "confirmation": confirmation,
        "provider": provider,
        "guest_name": booking.get("guest_name", ""),
        "check_in": check_in,
        "check_out": check_out,
        "check_in_time": booking.get("check_in_time", ""),
        "check_out_time": booking.get("check_out_time", ""),
        "city": city,
        "street_address": booking.get("street_address", ""),
        "postal_code": booking.get("postal_code", ""),
        "latitude": str(booking.get("latitude", "")) if booking.get("latitude") else "",
        "longitude": str(booking.get("longitude", "")) if booking.get("longitude") else "",
        "amount_paid": booking.get("amount_paid", ""),
        "amount_total": booking.get("amount_total", ""),
        "room_type": booking.get("room_type", ""),
        "breakfast_included": str(booking.get("breakfast_included", False)).lower(),
        "website": str(booking.get("website", "")),
    }

    frontmatter_lines = ["---"]
    for key, value in frontmatter_fields.items():
        if value:
            # Escape quotes in YAML values
            safe_value = str(value).replace('"', '\\"')
            frontmatter_lines.append(f'{key}: "{safe_value}"')
    frontmatter_lines.append("---")

    body_lines = [
        f"# {provider} - {city}",
        "",
        f"**Confirmation:** {confirmation}",
        f"**Check-in:** {check_in} at {booking.get('check_in_time', 'N/A')}",
        f"**Check-out:** {check_out} at {booking.get('check_out_time', 'N/A')}",
        "",
    ]

    if booking.get("street_address"):
        body_lines.append(f"**Address:** {booking['street_address']}, {city} {booking.get('postal_code', '')}")
    if booking.get("room_type"):
        body_lines.append(f"**Room:** {booking['room_type']}")
    if booking.get("amount_total"):
        body_lines.append(f"**Total:** {booking['amount_total']}")
    if booking.get("cancellation_terms"):
        body_lines.append(f"**Cancellation:** {booking['cancellation_terms']}")

    content = "\n".join(frontmatter_lines) + "\n\n" + "\n".join(body_lines) + "\n"
    filename = f"{check_in}_{provider}_{confirmation}.md".replace(" ", "_").replace("/", "-")

    return ObsidianBookingNote(filename=filename, content=content)


def _city_to_markdown(city_data: dict, trip_name: Optional[str] = None) -> ObsidianBookingNote:
    """Convert a city dict to an Obsidian-compatible markdown note."""
    city_name = city_data.get("city_name", "Unknown")
    country = city_data.get("country", "")
    city_id = city_data.get("city_id", city_data.get("confirmation", ""))

    visits = city_data.get("visits") or []
    trip_visits = visits
    if trip_name:
        trip_visits = [v for v in visits if v.get("trip") == trip_name]

    frontmatter_fields = {
        "type": "city",
        "city_id": city_id,
        "city_name": city_name,
        "country": country,
        "state": city_data.get("state", ""),
        "latitude": str(city_data.get("latitude", "")) if city_data.get("latitude") else "",
        "longitude": str(city_data.get("longitude", "")) if city_data.get("longitude") else "",
        "location_name": city_data.get("location_name", ""),
    }

    if trip_name:
        frontmatter_fields["trip"] = trip_name

    frontmatter_lines = ["---"]
    for key, value in frontmatter_fields.items():
        if value:
            safe_value = str(value).replace('"', '\\"')
            frontmatter_lines.append(f'{key}: "{safe_value}"')
    frontmatter_lines.append("---")

    body_lines = [
        f"# {city_name}, {country}",
        "",
    ]

    if city_data.get("location_name"):
        body_lines.append(f"**Location:** {city_data['location_name']}")

    if trip_visits:
        body_lines.append("")
        body_lines.append("## Visits")
        for visit in trip_visits:
            body_lines.append(f"- **{visit.get('trip', 'N/A')}:** {visit.get('start_date', '?')} to {visit.get('end_date', '?')}")

    content = "\n".join(frontmatter_lines) + "\n\n" + "\n".join(body_lines) + "\n"
    filename = f"{city_name}_{country}.md".replace(" ", "_").replace("/", "-")

    return ObsidianBookingNote(filename=filename, content=content)


@router.get("/obsidian/trips/{trip_name}", response_model=ObsidianTripExport)
async def export_trip_for_obsidian(trip_name: str):
    """
    Export a trip as Obsidian-compatible markdown notes with YAML frontmatter.
    Returns an overview note and individual booking/city notes.
    """
    with logfire.span("export_obsidian_trip", trip_name=trip_name):
        cities = db_service.get_cities_by_trip(trip_name)
        if not cities:
            raise HTTPException(status_code=404, detail=f"No cities found for trip: {trip_name}")

        # Get trip date range for booking lookup
        start_dates = []
        end_dates = []
        for city in cities:
            for visit in (city.get("visits") or []):
                if visit.get("trip") == trip_name:
                    start_dates.append(visit.get("start_date", ""))
                    end_dates.append(visit.get("end_date", ""))

        # Fetch bookings in the trip date range
        bookings = []
        if start_dates and end_dates:
            min_start = min(d for d in start_dates if d)
            max_end = max(d for d in end_dates if d)
            if min_start and max_end:
                bookings = db_service.get_bookings_by_date_range(
                    start_date=min_start,
                    end_date=max_end,
                    date_field="check_in_date",
                )

        # Generate individual notes
        booking_notes = [_booking_to_markdown(b) for b in bookings]
        city_notes = [_city_to_markdown(c, trip_name) for c in cities]

        # Generate overview note
        overview_lines = [
            "---",
            f'type: "trip"',
            f'trip: "{trip_name}"',
            "---",
            "",
            f"# {trip_name}",
            "",
            "## Cities",
        ]
        for city in cities:
            city_name = city.get("city_name", "")
            country = city.get("country", "")
            for visit in (city.get("visits") or []):
                if visit.get("trip") == trip_name:
                    overview_lines.append(
                        f"- [[{city_name}_{country}|{city_name}, {country}]] "
                        f"({visit.get('start_date', '?')} to {visit.get('end_date', '?')})"
                    )

        if bookings:
            overview_lines.append("")
            overview_lines.append("## Bookings")
            for b in bookings:
                provider = b.get("provider_name", "")
                confirmation = b.get("confirmation", "")
                check_in = b.get("check_in_date", "")
                city = b.get("city", "")
                filename = f"{check_in}_{provider}_{confirmation}".replace(" ", "_").replace("/", "-")
                overview_lines.append(f"- [[{filename}|{provider} in {city}]] ({check_in})")

        overview = "\n".join(overview_lines) + "\n"

        return ObsidianTripExport(
            trip_name=trip_name,
            overview=overview,
            booking_notes=booking_notes,
            city_notes=city_notes,
        )


@router.get("/obsidian/bookings", response_model=list[ObsidianBookingNote])
async def export_bookings_for_obsidian(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Export bookings as Obsidian-compatible markdown notes."""
    with logfire.span("export_obsidian_bookings"):
        bookings = db_service.get_bookings_by_date_range(
            start_date=start_date,
            end_date=end_date,
            date_field="check_in_date",
        )
        return [_booking_to_markdown(b) for b in bookings]
