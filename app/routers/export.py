"""
FastAPI router for Obsidian export endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import Optional
from datetime import datetime
from app.schemas.booking import ObsidianTripExport, ObsidianTripNote, ObsidianBookingNote, BookingResponse
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


def _format_date_range(start: str, end: str) -> str:
    """Format date range for display, e.g. 'December 6 - 9' or 'December 28 - January 2'."""
    try:
        from datetime import datetime as dt
        s = dt.strptime(start, "%Y-%m-%d")
        e = dt.strptime(end, "%Y-%m-%d")
        if s.month == e.month:
            return f"{s.strftime('%B')} {s.day} - {e.day}"
        return f"{s.strftime('%B')} {s.day} - {e.strftime('%B')} {e.day}"
    except (ValueError, TypeError):
        return f"{start} - {end}"


def _clean(value) -> str:
    """Strip <UNKNOWN>, buggy 'True'/'False', and None values."""
    if not value:
        return ""
    s = str(value).strip()
    if s in ("<UNKNOWN>", "True", "False", "None", "unknown"):
        return ""
    return s


def _format_hotel_lines(b: dict) -> list:
    """Format a hotel booking as markdown lines."""
    lines = []
    provider = _clean(b.get("provider_name", ""))
    if provider:
        lines.append(provider)

    breakfast = b.get("breakfast_included")
    if breakfast is True:
        lines.append("Breakfast included")
    elif breakfast is False:
        lines.append("Breakfast not included")

    check_in_time = _clean(b.get("check_in_time", ""))
    check_out_time = _clean(b.get("check_out_time", ""))
    if check_in_time or check_out_time:
        lines.append(f"Check-in and Out: {check_in_time or 'N/A'} / {check_out_time or 'N/A'}")

    lines.append("")

    address_parts = []
    for field in ("street_address", "city", "postal_code"):
        val = _clean(b.get(field, ""))
        if val:
            address_parts.append(val)
    if address_parts:
        lines.append(", ".join(address_parts))

    website = _clean(str(b.get("website", "")) if b.get("website") else "")
    if website:
        lines.append(website)

    conf = _clean(b.get("confirmation", ""))
    if conf:
        lines.append(conf)

    return lines


def _format_arrival_lines(b: dict) -> list:
    """Format a transit booking as arrival lines (destination-focused)."""
    lines = []
    parts = []
    provider = _clean(b.get("provider_name", ""))
    route = _clean(b.get("route_number", ""))
    arr_time = _clean(b.get("check_out_time", ""))
    arr_station = _clean(b.get("arrival_station", ""))

    if provider:
        parts.append(provider)
    if route:
        parts.append(route)
    if arr_time:
        parts.append(arr_time)
    if arr_station:
        parts.append(arr_station)
    if parts:
        lines.append(" ".join(parts))

    conf = _clean(b.get("confirmation", ""))
    if conf:
        lines.append(conf)

    return lines


def _format_departure_lines(b: dict) -> list:
    """Format a transit booking as departure lines (full route)."""
    lines = []
    provider = _clean(b.get("provider_name", ""))
    route = _clean(b.get("route_number", ""))

    header = " ".join(p for p in [provider, route] if p)
    if header:
        lines.append(header)

    dep_station = _clean(b.get("departure_station", ""))
    dep_time = _clean(b.get("check_in_time", ""))
    dep_line = " ".join(p for p in [dep_station, dep_time] if p)
    if dep_line:
        lines.append(dep_line)

    arr_station = _clean(b.get("arrival_station", ""))
    arr_time = _clean(b.get("check_out_time", ""))
    arr_line = " ".join(p for p in [arr_station, arr_time] if p)
    if arr_line:
        lines.append(arr_line)

    conf = _clean(b.get("confirmation", ""))
    if conf:
        lines.append(conf)

    return lines


def _match_transit_arrival(transit_bookings: list, city_name: str, arrival_date: str) -> list:
    """Find transit bookings arriving at this city on this date."""
    if not arrival_date:
        return []
    name_lower = city_name.lower()
    matched = []
    for b in transit_bookings:
        arr_city = _clean(b.get("arrival_city", "")).lower()
        dep_date = b.get("check_in_date", "")
        out_date = b.get("check_out_date", "")
        # Match by arrival_city + date, or by check_out_date (arrival date) matching visit start
        if arr_city == name_lower and (dep_date == arrival_date or out_date == arrival_date):
            matched.append(b)
        elif not arr_city and out_date == arrival_date:
            # Fallback: no arrival_city set, but arrival date matches
            b_city = _clean(b.get("city", "")).lower()
            if b_city != name_lower:
                # city field is departure city, this is arriving somewhere else — could be us
                matched.append(b)
    return matched


def _match_transit_departure(transit_bookings: list, city_name: str, departure_date: str) -> list:
    """Find transit bookings departing from this city on this date."""
    if not departure_date:
        return []
    name_lower = city_name.lower()
    matched = []
    for b in transit_bookings:
        dep_city = _clean(b.get("departure_city", "")).lower()
        dep_date = b.get("check_in_date", "")
        if dep_city == name_lower and dep_date == departure_date:
            matched.append(b)
        elif not dep_city:
            # Fallback: no departure_city, use city field
            b_city = _clean(b.get("city", "")).lower()
            if b_city == name_lower and dep_date == departure_date:
                matched.append(b)
    return matched


@router.get("/obsidian/trip-note/{trip_name}", response_model=ObsidianTripNote)
async def export_trip_note_for_obsidian(trip_name: str):
    """
    Export a trip as a single consolidated Obsidian markdown note.
    City-centric itinerary format with Arrival/Hotel/Departure per city visit.
    """
    with logfire.span("export_obsidian_trip_note", trip_name=trip_name):
        cities = db_service.get_cities_by_trip(trip_name)
        if not cities:
            raise HTTPException(status_code=404, detail=f"No cities found for trip: {trip_name}")

        # Get trip date range for booking lookup
        start_dates = []
        end_dates = []
        for city in cities:
            for visit in (city.get("visits") or []):
                if visit.get("trip") == trip_name:
                    if visit.get("start_date"):
                        start_dates.append(visit["start_date"])
                    if visit.get("end_date"):
                        end_dates.append(visit["end_date"])

        # Fetch bookings in the trip date range
        bookings = []
        if start_dates and end_dates:
            min_start = min(start_dates)
            max_end = max(end_dates)
            bookings = db_service.get_bookings_by_date_range(
                start_date=min_start,
                end_date=max_end,
                date_field="check_in_date",
            )

        # Separate bookings by type
        hotel_bookings = [b for b in bookings if b.get("booking_type", "hotel") not in ("train", "flight")]
        transit_bookings = [b for b in bookings if b.get("booking_type") in ("train", "flight")]

        # Build flat visit list sorted by start_date
        visit_list = []
        for city in cities:
            city_name = city.get("city_name", "")
            for v in (city.get("visits") or []):
                if v.get("trip") == trip_name:
                    visit_list.append({
                        "city_name": city_name,
                        "start_date": v.get("start_date") or "",
                        "end_date": v.get("end_date") or "",
                    })
        visit_list.sort(key=lambda x: x["start_date"] or "9999")

        # Count days
        total_days = 0
        if start_dates and end_dates:
            try:
                from datetime import datetime as dt
                s = dt.strptime(min(start_dates), "%Y-%m-%d")
                e = dt.strptime(max(end_dates), "%Y-%m-%d")
                total_days = (e - s).days
            except (ValueError, TypeError):
                pass

        # Build the note
        now = datetime.utcnow().isoformat(timespec="seconds")
        lines = [
            "---",
            f'parent: "[[Travel]]"',
            "type: travel-sync",
            f'trip: "{trip_name}"',
            f'synced_at: "{now}"',
            f'decimalLink: "[[15.52 Active Trips]]"',
            "---",
        ]

        # Summary section
        lines.append("")
        lines.append("# Summary")
        if total_days:
            lines.append(f"### Days:")
            lines.append(f"{total_days}")

        # Track used booking IDs to detect unmatched
        used_hotel_ids = set()
        used_transit_ids = set()

        # City-centric itinerary
        for visit in visit_list:
            city_name = visit["city_name"]
            v_start = visit["start_date"]
            v_end = visit["end_date"]

            lines.append("")
            lines.append(f"# {city_name}")
            lines.append(f"[[{city_name}]]")

            # Arrival
            arrivals = _match_transit_arrival(transit_bookings, city_name, v_start)
            if arrivals:
                lines.append("## Arrival")
                for i, b in enumerate(arrivals):
                    used_transit_ids.add(b.get("confirmation", ""))
                    if i == 0:
                        lines.extend(_format_arrival_lines(b))
                    else:
                        # Additional arrivals as Local
                        lines.append("### Local")
                        lines.extend(_format_arrival_lines(b))

            # Hotel
            city_hotels = [
                b for b in hotel_bookings
                if (_clean(b.get("city", "")).lower() == city_name.lower()
                    and b.get("check_in_date", "") >= v_start
                    and b.get("check_in_date", "") <= (v_end or "9999")
                    and b.get("confirmation") not in used_hotel_ids)
            ]
            city_hotels.sort(key=lambda b: b.get("check_in_date") or "")
            for b in city_hotels:
                used_hotel_ids.add(b.get("confirmation", ""))
                lines.append("## Hotel")
                lines.extend(_format_hotel_lines(b))

            # Departure
            departures = _match_transit_departure(transit_bookings, city_name, v_end)
            if departures:
                lines.append("## Departure")
                for i, b in enumerate(departures):
                    used_transit_ids.add(b.get("confirmation", ""))
                    if i > 0:
                        # Additional departures as Local before main
                        lines.append("### Local")
                    lines.extend(_format_departure_lines(b))

        # Unmatched bookings
        unmatched_hotels = [b for b in hotel_bookings if b.get("confirmation") not in used_hotel_ids]
        unmatched_transit = [b for b in transit_bookings if b.get("confirmation") not in used_transit_ids]
        if unmatched_hotels or unmatched_transit:
            lines.append("")
            lines.append("# Unmatched Bookings")
            for b in unmatched_hotels:
                city = _clean(b.get("city", "")) or "Unknown"
                lines.append(f"## {city} Hotel")
                lines.extend(_format_hotel_lines(b))
            for b in unmatched_transit:
                provider = _clean(b.get("provider_name", ""))
                lines.append(f"## {provider or 'Transit'}")
                lines.extend(_format_departure_lines(b))

        content = "\n".join(lines) + "\n"
        filename = f"{trip_name} Trip Reservations.md"

        return ObsidianTripNote(
            trip_name=trip_name,
            filename=filename,
            content=content,
        )


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
