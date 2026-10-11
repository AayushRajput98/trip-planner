from typing import Any

from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..models import Booking
from ..services import trip_service

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.get("")
def list_bookings():
    return trip_service.list_bookings()


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
