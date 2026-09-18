from typing import Any

from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..services import trip_service

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("")
def get_meta():
    return trip_service.get_meta()


@router.put("", dependencies=[Depends(require_auth)])
def update_meta(patch: dict[str, Any]):
    return trip_service.update_meta(patch)
