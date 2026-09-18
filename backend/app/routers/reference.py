from typing import Any

from fastapi import APIRouter, Body, Depends

from ..auth import require_auth
from ..services import trip_service

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/{section}")
def get_reference(section: str):
    return trip_service.get_reference(section)


@router.put("/{section}", dependencies=[Depends(require_auth)])
def update_reference(section: str, data: Any = Body(...)):
    return trip_service.update_reference(section, data)
