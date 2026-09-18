from typing import Any

from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..services import trip_service

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("")
def get_budget():
    return trip_service.get_budget()


@router.put("", dependencies=[Depends(require_auth)])
def update_budget(patch: dict[str, Any]):
    return trip_service.update_budget(patch)
