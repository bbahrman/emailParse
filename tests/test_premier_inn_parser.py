import pathlib
from datetime import date

import pytest

from app.models.booking import Booking


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


def load_email(name: str) -> str:
    """Helper to load raw email content from fixtures."""
    path = FIXTURE_DIR / name
    return path.read_text(encoding="utf-8")


def test_parse_premier_inn_booking_basic():
    raw_email = load_email("premier_inn_booking_maq1101970.eml")

    booking = parse_premier_inn_booking(raw_email)

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

    # Pydantic HttpUrl will normalize, so we compare the string form
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
    raw_email = load_email("premier_inn_booking_maq1101970.eml")
    booking = parse_premier_inn_booking(raw_email)

    assert hasattr(booking, attr_name), f"Missing attribute: {attr_name}"

    value = getattr(booking, attr_name)
    # For dates / other non-str fields, just assert not None
    if isinstance(value, (str,)):
        assert value.strip() != "", f"Empty string for attribute: {attr_name}"
    else:
        assert value is not None, f"None value for attribute: {attr_name}"
