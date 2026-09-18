from fastapi import APIRouter

from ..services import trip_service

router = APIRouter(prefix="/api", tags=["trip"])


@router.get("/trip")
def get_trip():
    return trip_service.get_trip()
