import json
from datetime import datetime
from app.models.booking import ExtractionResult, get_extract_booking_tool
from app.llm.client import client
import logfire

logfire.configure()


def _normalize_date(date_str: str) -> str:
    """Try to parse various date formats and return ISO format (YYYY-MM-DD)."""
    if not date_str or date_str == "<UNKNOWN>":
        return date_str

    # Already ISO format
    if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str

    formats = [
        "%d/%m/%Y",           # 12/05/2026
        "%m/%d/%Y",           # 05/12/2026
        "%B %d, %Y",         # May 12, 2026
        "%b %d, %Y",         # May 12, 2026
        "%A, %B %d, %Y",    # Saturday, May 9, 2026
        "%d %B %Y",          # 12 May 2026
        "%d %b %Y",          # 12 May 2026
        "%Y-%m-%dT%H:%M:%S", # 2026-05-12T00:00:00
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    logfire.warning("Could not normalize date", date_str=date_str)
    return date_str


def _normalize_booking_dates(result: ExtractionResult) -> ExtractionResult:
    """Normalize all date fields in an extraction result to ISO format."""
    if not result.booking:
        return result

    b = result.booking
    date_fields = ["check_in_date", "check_out_date", "booking_date"]
    for field in date_fields:
        val = getattr(b, field, None)
        if val:
            setattr(b, field, _normalize_date(val))

    return result


def llm_extract_email(email_text: str) -> ExtractionResult:
    with logfire.span("llm_extract_email", email_length=len(email_text)):
        tool = get_extract_booking_tool()
        prompt = """
    You are an email parsing assistant.

    The user will send you RAW email text (headers, HTML, bodies, weird formatting)
    representing either a booking (hotel, car, plane, train, tour, etc) OR a marketing email

    Your job:
    1. Determine if this is a BOOKING email or MARKETING email.
    2. If booking, extract all booking details.
    3. If marketing, set kind="marketing" and booking=null.

    IMPORTANT rules:
    - ALL dates MUST be in ISO format: YYYY-MM-DD (e.g., 2026-05-12)
    - Convert any date format you see to ISO format
    - For check_in_date, check_out_date, and booking_date: always use YYYY-MM-DD
    - Set booking_type to one of: "hotel", "train", "flight", "car", "tour", "other"

    For HOTEL bookings:
    - departure_city, arrival_city, departure_station, arrival_station, route_number, seat_class, seat_number can be empty

    For TRANSIT bookings (train, flight):
    - departure_city: city of departure (e.g., "London")
    - arrival_city: city of arrival (e.g., "York")
    - departure_station: station or airport name (e.g., "Kings Cross", "LHR Terminal 5")
    - arrival_station: station or airport name (e.g., "York", "Paddington")
    - route_number: flight number or train service (e.g., "BA123", "GWR 12:30")
    - seat_class: class of travel (e.g., "Standard", "First Class", "Business")
    - seat_number: seat assignment if available (e.g., "42A", "Coach C Seat 14")
    - check_in_date/check_in_time = departure date/time
    - check_out_date/check_out_time = arrival date/time
    - city = departure_city
    - street_address = departure_station

    OUTPUT:
    Use the extract_booking tool.
        """.strip()

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=prompt,
            messages=[
                {"role": "user", "content": email_text},
            ],
            tools=[tool],
            tool_choice={"type": "tool", "name": "extract_booking"},
        )
        logfire.info("LLM response", stop_reason=response.stop_reason)

        # Extract tool use result from response content blocks
        for block in response.content:
            if block.type == "tool_use":
                logfire.info("LLM tool_use", tool_input=block.input)
                result = ExtractionResult(**block.input)
                return _normalize_booking_dates(result)

        raise ValueError("No tool_use block found in Claude response")
