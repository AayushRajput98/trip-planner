from typing import Any

from fastapi import APIRouter, Depends, UploadFile

from ..auth import require_auth
from ..models import Booking
from ..parsing import parse_booking_pdf
from ..services import trip_service
from .uploads import store_upload

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.get("")
def list_bookings():
    return trip_service.list_bookings()


@router.post("/parse", dependencies=[Depends(require_auth)])
async def parse_booking(file: UploadFile):
    """Best-effort extraction of hotel/city/dates/cost from an uploaded
    invoice PDF, plus the stored receipt it can be attached to. Never
    raises on a parse miss — any field it couldn't find comes back as
    None and the frontend shows an editable form, since a heuristic
    parser across arbitrary OTA templates will sometimes get it wrong."""
    data = await file.read()
    receipt = store_upload(data, file.filename or "invoice.pdf")
    try:
        parsed = parse_booking_pdf(data)
    except Exception:
        parsed = {"hotel": None, "city": None, "checkIn": None, "checkOut": None,
                   "amount": None, "currency": None, "confirmationNumber": None}
    return {**parsed, "receipt": receipt}


@router.post("", dependencies=[Depends(require_auth)])
def add_booking(booking: Booking):
    return trip_service.add_booking(booking.model_dump(exclude_none=True))


@router.put("/{booking_id}", dependencies=[Depends(require_auth)])
def update_booking(booking_id: str, patch: dict[str, Any]):
    return trip_service.update_booking(booking_id, patch)


@router.delete("/{booking_id}", dependencies=[Depends(require_auth)])
def delete_booking(booking_id: str):
    trip_service.delete_booking(booking_id)
    return {"ok": True}
