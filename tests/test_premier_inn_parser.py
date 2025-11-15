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


def test_parse_premier_inn_booking_basic():
    raw_email = load_email("premier_inn_booking_maq1101970.eml")

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
def test_all_expected_fields_populated(attr_name: str):
    """Ensure all expected attributes exist and are non-empty."""
    raw_email = load_email("hub_premier_inn_test.eml")  # drop extra .eml if typo
    booking = parse_email(raw_email)

    assert hasattr(booking, attr_name), f"Missing attribute: {attr_name}"

    value = getattr(booking, attr_name)
    # For str fields, assert non-empty trimmed; otherwise just non-None
    if isinstance(value, str):
        assert value.strip() != "", f"Empty string for attribute: {attr_name}"
    else:
        assert value is not None, f"None value for attribute: {attr_name}"
