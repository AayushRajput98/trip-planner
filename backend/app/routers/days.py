from typing import Any

from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..models import StatusUpdate
from ..services import trip_service

router = APIRouter(prefix="/api/days", tags=["days"])


@router.get("")
def list_days():
    return trip_service.list_days()


@router.post("", dependencies=[Depends(require_auth)])
def add_day(day: dict[str, Any]):
    return trip_service.add_day(day)


@router.post("/reorder", dependencies=[Depends(require_auth)])
def reorder_days(order: list[str]):
    return trip_service.reorder_days(order)


@router.get("/{n}")
def get_day(n: str):
    return trip_service.get_day(n)


@router.put("/{n}", dependencies=[Depends(require_auth)])
def update_day(n: str, patch: dict[str, Any]):
    return trip_service.update_day(n, patch)


@router.delete("/{n}", dependencies=[Depends(require_auth)])
def delete_day(n: str):
    trip_service.delete_day(n)
    return {"ok": True}


@router.put("/{n}/timetable/{index}/status", dependencies=[Depends(require_auth)])
def set_timetable_status(n: str, index: int, body: StatusUpdate):
    return trip_service.set_timetable_status(n, index, body.status)
