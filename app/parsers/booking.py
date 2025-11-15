from __future__ import annotations

from email import message_from_string, policy
from app.llm.extractors import llm_extract_email


def _extract_html_from_email(raw_email: str) -> str:
    """Return the HTML body if present; fallback to raw email text."""
    msg = message_from_string(raw_email, policy=policy.default)

    # Try HTML part
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")

    # Single-part email
    if msg.get_content_type() == "text/html":
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    # Fallback
    return raw_email

def parse_email(raw_email: str):
    """Extract HTML → send to LLM → return ExtractionResult."""
    html = _extract_html_from_email(raw_email)
    return llm_extract_email(html)



