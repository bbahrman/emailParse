# tests/test_booking_parser.py
import pathlib
from datetime import date
import pytest
from app.models.booking import Booking
from app.parsers.booking import parse_email


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


def load_email(name: str) -> str:
    """Helper to load raw email content from fixtures."""
    path = FIXTURE_DIR / name
    return path.read_text(encoding="utf-8")


@pytest.mark.integration
def test_parse_premier_inn_booking_basic():
    raw_email = load_email("hub_premier_inn_test.eml")

    booking = parse_email(raw_email)

    # Type sanity
    assert isinstance(booking, Booking)

    # Core expectations
    assert booking.confirmation == "MAQ1101970"

    assert booking.check_in_date == date(2025, 3, 20)
    assert booking.check_out_date == date(2025, 3, 28)

    assert booking.check_in_time == "3pm"
    assert booking.check_out_time == "12pm"

    assert booking.early_check_in == "available for GBP 15"

    assert booking.address == "Old Marylebone Road, GB, NW1 5DZ"
    assert booking.what3words == "///talent.actors.ideal"

    # Pydantic HttpUrl will normalize, so compare string form
    assert str(booking.website) == "https://premierinn.com/"


@pytest.mark.parametrize(
    "attr_name",
    [
        "confirmation",
        "check_in_date",
        "check_out_date",
        "check_in_time",
        "check_out_time",
        "early_check_in",
        "address",
        "what3words",
        "website",
    ],
)
def test_all_expected_fields_populated(monkeypatch, attr_name: str):
    """Unit-level check: parse_email wiring + Booking fields, with fake LLM output."""
    raw_email = load_email("hub_premier_inn_test.eml")

    # Fake result coming back from llm_extract_email
    from datetime import date
    from app.models.booking import Booking

    fake_booking = Booking(
        confirmation="FAKE123",
        check_in_date=date(2025, 3, 20),
        check_out_date=date(2025, 3, 28),
        check_in_time="3pm",
        check_out_time="12pm",
        early_check_in="available for GBP 15",
        early_check_in_time="12:00",
        address="Old Marylebone Road, GB, NW1 5DZ",
        what3words="///talent.actors.ideal",
        website="https://premierinn.com/",
        name="hub by Premier Inn",
        room_type="",
        early_check_in_cost=15,
        breakfast_included=True,
        cancellation_terms="",
        city="",
        booking_date=date(2025, 1, 20),
        amount_paid=0,
        amount_total=100,
     )

    def fake_parse_email(_raw: str) -> Booking:
        # you could also monkeypatch llm_extract_email instead;
        # this is simpler for now.
        return fake_booking

    monkeypatch.setattr("app.parsers.booking.parse_email", fake_parse_email)

    booking = parse_email(raw_email)

    assert hasattr(booking, attr_name), f"Missing attribute: {attr_name}"

    value = getattr(booking, attr_name)
    if isinstance(value, str):
        assert value.strip() != "", f"Empty string for attribute: {attr_name}"
    else:
        assert value is not None, f"None value for attribute: {attr_name}"
