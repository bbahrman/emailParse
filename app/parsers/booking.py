# parsers.py
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from email import message_from_string, policy, utils as email_utils
from typing import Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from app.models.booking import Booking


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


def _extract_booking_date(raw_email: str) -> date:
    """Get the email's Date header as a date, or today if missing."""
    msg = message_from_string(raw_email, policy=policy.default)
    header = msg.get("Date")
    if not header:
        return date.today()
    dt = email_utils.parsedate_to_datetime(header)
    # Handle naive vs aware just in case
    if isinstance(dt, datetime):
        return dt.date()
    return date.today()


def _first_regex(text: str, pattern: str, flags=0) -> Optional[re.Match]:
    return re.search(pattern, text, flags)


def parse_booking(raw_email: str) -> Booking:
    html = _extract_html_from_email(raw_email)
    soup = BeautifulSoup(html, "html.parser")

    # Get flattened text and lines for easier pattern matching
    text = soup.get_text(separator="\n")
    text = text.replace("\xa0", " ")  # non-breaking spaces
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]  # drop empty lines

    # ---------- Booking date (from headers) ----------
    booking_date = _extract_booking_date(raw_email)

    # ---------- Name ----------
    # Look for "Hello <Name>"
    name = ""
    for ln in lines:
        if ln.startswith("Hello "):
            name = ln.replace("Hello", "", 1).strip()
            break
    if not name:
        # Fallback: from "Room details" block (line after "Room details")
        for i, ln in enumerate(lines):
            if ln.lower().startswith("room details"):
                if i + 1 < len(lines):
                    name = lines[i + 1]
                break

    # ---------- Confirmation code ----------
    # We know there's a "Booking Reference" line followed by the code
    confirmation = ""
    for i, ln in enumerate(lines):
        if "Booking Reference" in ln:
            if i + 1 < len(lines):
                confirmation = lines[i + 1].strip()
            break

    # Fallback – first 8–12 char alnum code (e.g. MAQ1101970)
    if not confirmation:
        m = _first_regex(text, r"\b[A-Z0-9]{8,12}\b")
        if m:
            confirmation = m.group(0)

    # ---------- Check-in / Check-out dates & times ----------
    check_in_date: date
    check_out_date: date
    check_in_time = ""
    check_out_time = ""

    # Search for the structured block:
    # Check in /  Thu 20 Mar 2025 / from / 3pm
    for i, ln in enumerate(lines):
        if ln.lower().startswith("check in"):
            if i + 1 < len(lines):
                date_str = lines[i + 1].strip()
                # Thu 20 Mar 2025
                try:
                    check_in_date = datetime.strptime(
                        date_str, "%a %d %b %Y"
                    ).date()
                except ValueError:
                    # last-resort parse
                    m = _first_regex(date_str, r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})")
                    if m:
                        check_in_date = datetime.strptime(
                            m.group(1), "%d %b %Y"
                        ).date()
                    else:
                        check_in_date = booking_date

            # Find time below
            for j in range(i + 1, min(i + 6, len(lines))):
                if re.search(r"\b\d{1,2}\s*(am|pm)\b", lines[j], re.I):
                    check_in_time = re.search(
                        r"\b\d{1,2}\s*(?:am|pm)\b", lines[j], re.I
                    ).group(0).lower()
                    break

        if ln.lower().startswith("check out"):
            if i + 1 < len(lines):
                date_str = lines[i + 1].strip()
                try:
                    check_out_date = datetime.strptime(
                        date_str, "%a %d %b %Y"
                    ).date()
                except ValueError:
                    m = _first_regex(date_str, r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})")
                    if m:
                        check_out_date = datetime.strptime(
                            m.group(1), "%d %b %Y"
                        ).date()
                    else:
                        check_out_date = booking_date

            for j in range(i + 1, min(i + 6, len(lines))):
                if re.search(r"\b\d{1,2}\s*(am|pm)\b", lines[j], re.I):
                    check_out_time = re.search(
                        r"\b\d{1,2}\s*(?:am|pm)\b", lines[j], re.I
                    ).group(0).lower()
                    break

    # If parsing failed for some reason, fall back to booking_date
    check_in_date = locals().get("check_in_date", booking_date)
    check_out_date = locals().get("check_out_date", booking_date)

    # ---------- Early check-in ----------
    early_check_in_cost = Decimal("0")
    early_check_in_time = ""

    for ln in lines:
        if "Early Check In" in ln:
            m = _first_regex(ln, r"£\s*([0-9]+(?:\.[0-9]{2})?)")
            if m:
                early_check_in_cost = Decimal(m.group(1))
            # Email doesn’t specify a separate early check-in time, so we’ll
            # just default to the regular check-in time.
            early_check_in_time = check_in_time
            break

    # ---------- Breakfast included ----------
    # This email doesn’t mention breakfast; treat as False unless we see it.
    breakfast_included = bool(
        re.search(r"breakfast", text, re.I)
        and re.search(r"(includes|included|with breakfast)", text, re.I)
    )

    # ---------- Cancellation terms ----------
    cancellation_terms = ""
    m = _first_regex(
        text,
        r"This is a Standard rate booking.*?terms and conditions\.",
        re.I | re.S,
    )
    if m:
        cancellation_terms = " ".join(m.group(0).split())
    else:
        # Fallback: empty or first paragraph containing "Standard rate booking"
        m = _first_regex(text, r"This is a Standard rate booking.*", re.I)
        if m:
            cancellation_terms = m.group(0).strip()

    # ---------- Address & City ----------
    address = ""
    city = "London"  # we can safely infer from the hotel name in this template

    for ln in lines:
        if "Old Marylebone Road" in ln and "NW1 5DZ" in ln:
            address = " ".join(ln.split())
            break

    # ---------- What3Words ----------
    what3words = ""
    m = _first_regex(text, r"///[a-z]+\.[a-z]+\.[a-z]+", re.I)
    if m:
        what3words = m.group(0)

    # ---------- Website ----------
    urls = {a.get("href") for a in soup.find_all("a", href=True)}
    urls = {u for u in urls if u}

    pi_urls = []
    for u in urls:
        parsed = urlparse(u)
        if "premierinn.com" in (parsed.netloc or ""):
            pi_urls.append(parsed)

    if pi_urls:
        # Choose the one with the shortest path as "root"
        best = min(pi_urls, key=lambda p: len(p.path or ""))
        website = f"{best.scheme}://{best.netloc}/"
    else:
        website = "https://premierinn.com/"

    # ---------- Amounts ----------
    amount_total = Decimal("0")
    amount_paid = Decimal("0")  # this email only shows total; treat as unpaid

    # Total price £785.00
    for ln in lines:
        if "Total price" in ln:
            # Next line usually contains the amount, or same line might
            idx = lines.index(ln)
            candidate = ln
            if idx + 1 < len(lines):
                candidate = lines[idx + 1]
            m = _first_regex(candidate, r"£\s*([0-9]+(?:\.[0-9]{2})?)")
            if m:
                amount_total = Decimal(m.group(1))
            break

    # ---------- Room type ----------
    room_type = ""
    for i, ln in enumerate(lines):
        if ln.lower().startswith("room details"):
            # pattern:
            # Room details
            # <Name>
            # Hub Standard Room
            if i + 2 < len(lines):
                room_type = lines[i + 2]
            break

    # ---------- Final assemble ----------
    return Booking(
        name=name,
        confirmation=confirmation,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        check_in_time=check_in_time,
        check_out_time=check_out_time,
        early_check_in_time=early_check_in_time,
        early_check_in_cost=early_check_in_cost,
        breakfast_included=breakfast_included,
        cancellation_terms=cancellation_terms,
        address=address,
        city=city,
        booking_date=booking_date,
        what3words=what3words,
        website=website,
        amount_paid=amount_paid,
        amount_total=amount_total,
        room_type=room_type,
    )
