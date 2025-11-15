import decimal
from datetime import date
from pydantic import BaseModel, HttpUrl
from typing import Optional


class Booking(BaseModel):
    name: str
    confirmation: str
    check_in_date: date
    check_out_date: date
    check_in_time: str
    check_out_time: str
    early_check_in_time: str
    early_check_in_cost: decimal.Decimal
    breakfast_included: bool
    cancellation_terms: str
    address: str
    city: str
    booking_date: date
    what3words: str
    website: HttpUrl
    amount_paid: decimal.Decimal
    amount_total: decimal.Decimal
    room_type: str


class ExtractionResult(BaseModel):
    kind: str
    booking: Optional[Booking]


def get_extract_booking_tool():
    return {
        "type": "function",
        "function": {
            "name": "extract_booking",
            "description": "Extracts booking information from an email.",
            "parameters": ExtractionResult.model_json_schema(),
        },
    }