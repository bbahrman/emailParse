# parsers.py
from __future__ import annotations

from email import message_from_string, policy
from app.llm.extractors import llm_extract_email

def _extract_html_from_email(raw_email: str) -> str:
    """Parse MIME and return the first text/html part; fall back to raw text."""
    msg = message_from_string(raw_email, policy=policy.default)

    # Try to find HTML part
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

    # Fallback – not ideal, but better than nothing
    return raw_email

raw_email = _extract_html_from_email()
parsed = llm_extract_email(raw_email)
print(parsed)



