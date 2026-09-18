from typing import Any

from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..services import trip_service

router = APIRouter(prefix="/api/checklist", tags=["checklist"])


@router.get("")
def get_checklist():
    return trip_service.get_checklist()


@router.post("", dependencies=[Depends(require_auth)])
def add_checklist_item(body: dict[str, Any]):
    return trip_service.add_checklist_item(body["text"])


@router.put("/{item_id}", dependencies=[Depends(require_auth)])
def set_checklist_item(item_id: str, patch: dict[str, Any]):
    return trip_service.set_checklist_item(item_id, patch)


@router.delete("/{item_id}", dependencies=[Depends(require_auth)])
def remove_checklist_item(item_id: str):
    trip_service.remove_checklist_item(item_id)
    return {"ok": True}
