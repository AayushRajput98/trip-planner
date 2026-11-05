"""Heuristic parser for hotel booking vouchers (PDF). Works across different
OTA templates (seen so far: MakeMyTrip's "Booking Voucher" and "Ticket"
layouts) without hardcoding to one provider's wording, by looking for
generic shapes — a currency-prefixed number, a "check-in"/"check-out"
label followed by a date, a line ending in a country code — rather than
exact phrases. It's a best-effort first pass: the frontend always shows the
result in an editable form before saving, since any single-provider wording
can change or a new provider can look completely different.
"""
import re
from collections import Counter
from io import BytesIO

from pypdf import PdfReader

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

DATE_RE = re.compile(
    r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s*)?(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})"
)
CURRENCY_RE = re.compile(r"(₹|INR|Rs\.?|\$|USD|EUR|€)\s?([0-9][0-9,]*(?:\.[0-9]{1,2})?)")
CURRENCY_NORM = {"₹": "INR", "INR": "INR", "RS": "INR", "RS.": "INR", "$": "USD", "USD": "USD", "€": "EUR", "EUR": "EUR"}
CITY_RE = re.compile(r"(?:,\s*|^)([A-Za-z][A-Za-z.'\- ]{1,30}?)\s*,\s*(?:[A-Z]{2}|India)\s*$")
CONF_PATTERNS = [
    re.compile(r"Hotel\s*Confirmation\s*Number\s*:?\s*([A-Za-z0-9]{4,})", re.IGNORECASE),
    re.compile(r"Booking\s*Id:?\s*([A-Za-z0-9]{4,})", re.IGNORECASE),
    re.compile(r"\bPNR:?\s*([A-Za-z0-9]{4,})", re.IGNORECASE),
]
DETAILS_HEADING_RE = re.compile(r"^(?:BOOKING|HOTEL|PROPERTY)\s*DETAILS$", re.IGNORECASE)
HOTEL_LINE_RE = re.compile(r"^Hotel\s+\S.*$")
CONFIRMED_AT_RE = re.compile(r"Your\s+Booking\s+at\s+(.+?)\s+is\s+Confirmed", re.IGNORECASE)


def extract_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _to_iso(day: str, month_name: str, year: str) -> str | None:
    month = MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def _find_date_near_label(lines: list[str], prefixes: tuple[str, ...]) -> str | None:
    """First line that *starts with* one of the label prefixes (e.g.
    "check-in"), case-insensitively — not just "contains", since prose like
    "...at the time of check in & collect at check-out." mentions the label
    mid-sentence without it being the actual date field. The date is either
    on that same line ("Check-in on 28 Nov 2026...") or the line right after
    (a standalone "Check-in" label followed by "Sun, 29 Nov 2026")."""
    for i, line in enumerate(lines):
        if not line.lower().startswith(prefixes):
            continue
        d = DATE_RE.search(line)
        if not d and i + 1 < len(lines):
            d = DATE_RE.search(lines[i + 1])
        if d:
            return _to_iso(*d.groups())
    return None


def _find_amount(flat: str) -> tuple[float | None, str | None]:
    candidates: Counter = Counter()
    for m in CURRENCY_RE.finditer(flat):
        prefix = flat[max(0, m.start() - 2):m.start()]
        if "-" in prefix:
            continue  # a discount/reversal line, not the actual charge
        currency = CURRENCY_NORM.get(m.group(1).upper(), "INR")
        amount = float(m.group(2).replace(",", ""))
        if amount <= 0:
            continue
        candidates[(currency, amount)] += 1
    if not candidates:
        return None, None
    (currency, amount), _ = candidates.most_common(1)[0]
    return amount, currency


def _find_hotel_name(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        if DETAILS_HEADING_RE.match(line) and i + 1 < len(lines):
            return lines[i + 1]
    for line in lines:
        if HOTEL_LINE_RE.match(line):
            return line
    return None


def _find_city(lines: list[str]) -> str | None:
    for line in lines:
        m = CITY_RE.search(line)
        if m:
            return m.group(1).strip().strip(",").strip()
    return None


def _find_confirmation_number(flat: str) -> str | None:
    for pattern in CONF_PATTERNS:
        m = pattern.search(flat)
        if m:
            return m.group(1)
    return None


def parse_booking_text(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    flat = re.sub(r"\s+", " ", text)

    hotel = _find_hotel_name(lines)
    if not hotel:
        m = CONFIRMED_AT_RE.search(flat)
        hotel = m.group(1).strip() if m else None

    amount, currency = _find_amount(flat)

    return {
        "hotel": hotel,
        "city": _find_city(lines),
        "checkIn": _find_date_near_label(lines, ("check-in", "check in")),
        "checkOut": _find_date_near_label(lines, ("check-out", "check out")),
        "amount": amount,
        "currency": currency,
        "confirmationNumber": _find_confirmation_number(flat),
    }


def parse_booking_pdf(data: bytes) -> dict:
    return parse_booking_text(extract_text(data))
