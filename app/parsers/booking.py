# app/parsers/booking.py
from __future__ import annotations

from email import message_from_string, policy
from app.llm.extractors import llm_extract_email
from app.models.booking import Booking, ExtractionResult
import logfire


def _extract_html_from_email(msg) -> str:
    """Return the HTML body if present; fallback to raw raw_email text."""
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
    return msg


def parse_email(raw_bytes: bytes) -> Booking:
    from email import message_from_bytes, policy
    with logfire.span("parse_email", email_size_raw=len(raw_bytes)):
        raw_email = message_from_bytes(raw_bytes, policy=policy.default)

        with logfire.span("extract_html_from_email"):
            html = _extract_html_from_email(raw_email)

        with logfire.span("llm_extract_booking"):
            result: ExtractionResult = llm_extract_email(html)

        if result.kind != "booking" or result.booking is None:
            raise ValueError("Email is not a booking or could not be parsed as one.")

        # result.booking is already a Booking (Pydantic model)
        return result.booking
