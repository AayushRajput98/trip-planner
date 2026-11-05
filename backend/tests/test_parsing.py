"""Unit tests for the heuristic voucher parser. Uses synthetic text shaped
like real OTA PDF extractions (not the user's own voucher files, which
carry personal data and shouldn't be committed) to pin down behavior across
the two layouts seen so far, plus a few targeted regression cases for bugs
found along the way (inline "check-out" mentioned mid-sentence, an address
line split across two physical lines, negative discount lines that must
not win the amount vote)."""
from app.parsing import parse_booking_text

# Shaped like a "Booking Voucher" template: hotel name on a "Hotel X" line,
# dates as standalone labels followed by the date on the next line, address
# wrapped across two lines ending "<city>, IN".
VOUCHER_STYLE = """
INR 4,200 You saved INR 600
Paid INR 4,200 with ICICI Bank
Paid Amount
Deluxe Room
2 Adults
Mr. Test Guest (Primary Guest)
Check-out
Wed, 10 Dec 2026
Before 11:00 AM
Check-in
Tue, 09 Dec 2026
After 12:00 PM
1-Night Stay
Hotel Sunrise Palace
Booking Id: XY11112222333
Hotel Confirmation Number : 555444
12 Lake Road, Near Fort, Testcity, Teststate, 100001,
Testcity, IN
Free Cancellation (100% refund) till Mon, 08 Dec 2026, 11:59 AM
"""

# Shaped like a "Ticket" template: an inline "Check-in on <date>" intro
# sentence, hotel name under a BOOKING DETAILS heading, "check-out" also
# appearing mid-sentence in unrelated prose before the real label, and a
# price breakup with negative discount lines that aren't the real total.
TICKET_STYLE = """
TICKET PNR:
0101010101
Booking Id:
XY99998888777
Your Booking at Riverside is Confirmed!
Check-in on 09 Dec 2026, 2:00 PM. (Booking Date: 01 Dec 2026 10:00 AM)
Full Amount of INR 1500 Has already been PAID.
BOOKING DETAILS
Riverside Guesthouse
Lake Side Road, Testville - 200002
, Testville, IN
2. Please inform for GST invoice at the time of check in & collect at check-out.
1 NIGHT STAY
Check-In
Tue, 09 Dec 2026
02:00 PM
Check-Out
Wed, 10 Dec 2026
11:00 AM
PRICE BREAKUP (in INR)
Accommodation charges 1600
Hotelier Discount - 100
TOTAL 1500
"""


def test_parses_voucher_style_template():
    result = parse_booking_text(VOUCHER_STYLE)
    assert result["hotel"] == "Hotel Sunrise Palace"
    assert result["city"] == "Testcity"
    assert result["checkIn"] == "2026-12-09"
    assert result["checkOut"] == "2026-12-10"
    assert result["amount"] == 4200.0
    assert result["currency"] == "INR"
    assert result["confirmationNumber"] == "555444"


def test_parses_ticket_style_template():
    result = parse_booking_text(TICKET_STYLE)
    assert result["hotel"] == "Riverside Guesthouse"
    assert result["city"] == "Testville"
    assert result["checkIn"] == "2026-12-09"
    # Regression: an inline "...collect at check-out." mid-sentence must not
    # be mistaken for the real "Check-Out" label a few lines later.
    assert result["checkOut"] == "2026-12-10"
    # Regression: the negative "- 100" discount line must not outvote the
    # one INR amount that actually repeats (the headline paid amount).
    assert result["amount"] == 1500.0
    assert result["currency"] == "INR"
    assert result["confirmationNumber"] == "XY99998888777"


def test_missing_fields_come_back_none_not_raise():
    result = parse_booking_text("This PDF has no recognizable booking fields at all.")
    assert result == {
        "hotel": None, "city": None, "checkIn": None, "checkOut": None,
        "amount": None, "currency": None, "confirmationNumber": None,
    }
