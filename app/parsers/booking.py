# app/parsers/booking.py
from __future__ import annotations

from email import message_from_string, policy
from app.llm.extractors import llm_extract_email
from app.models.booking import Booking, ExtractionResult


def _extract_html_from_email(raw_email: str) -> str:
    """Return the HTML body if present; fallback to raw raw_email text."""
    msg = message_from_string(raw_email, policy=policy.default)

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    else:
        if msg.get_content_type() == "text/html":
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")

    # Fallback – use the original raw email
    return raw_email


def parse_email(raw_email: str) -> Booking:
    """
    High-level parser:
    - Extract HTML body from raw email
    - Call LLM to extract structured booking info
    - Return a Booking instance

    Raises ValueError if this is not a booking email.
    """
    html = _extract_html_from_email(raw_email)
    result: ExtractionResult = llm_extract_email(html)

    if result.kind != "booking" or result.booking is None:
        raise ValueError("Email is not a booking or could not be parsed as one.")

    # result.booking is already a Booking (Pydantic model)
    return result.booking
