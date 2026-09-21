"""Version history, diffs, and restore — for whole resources (the History
timeline) and for individually deleted items within a collection (the trash
view). Reads are public like every other GET in this API; restoring requires
the same shared token as any other write.

Route order matters: the static "/feed" and "/trash..." paths are registered
before the "/{resource}..." family so they aren't swallowed by it."""
from fastapi import APIRouter, Depends

from .. import versioning
from ..auth import require_auth
from ..errors import NotFoundError, ValidationError
from ..resources import RESOURCE_ID_KEY
from ..services import trip_service

router = APIRouter(prefix="/api/versions", tags=["versions"])

RESTORE_ITEM_FN = {
    "days": lambda item: trip_service.add_day(item, op="restore_item"),
    "checklist": lambda item: trip_service.restore_checklist_item(item),
    "expenses": lambda item: trip_service.add_expense(item, op="restore_item"),
}


@router.get("/feed")
def get_feed(limit: int = 50):
    return versioning.feed(limit=limit)


@router.get("/trash")
def get_trash():
    rows = []
    for resource in RESOURCE_ID_KEY:
        rows.extend({"resource": resource, **row} for row in versioning.find_deleted_items(resource))
    rows.sort(key=lambda r: r["deletedAt"], reverse=True)
    return rows


@router.post("/trash/{resource}/{item_id}/restore", dependencies=[Depends(require_auth)])
def restore_trash_item(resource: str, item_id: str):
    if resource not in RESTORE_ITEM_FN:
        raise ValidationError(f"{resource!r} has no per-item trash (not a collection)")
    for row in versioning.find_deleted_items(resource):
        if str(row["id"]) == item_id:
            return RESTORE_ITEM_FN[resource](row["content"])
    raise NotFoundError(f"No deleted item {item_id!r} in {resource!r}")


@router.get("/{resource}")
def get_history(resource: str, limit: int | None = None):
    return versioning.list_history(resource, limit=limit)


@router.get("/{resource}/{version}")
def get_version(resource: str, version: int):
    return versioning.get_snapshot(resource, version)


@router.get("/{resource}/{version}/diff")
def get_version_diff(resource: str, version: int):
    return versioning.entry_diff(resource, version)


@router.post("/{resource}/{version}/restore", dependencies=[Depends(require_auth)])
def restore_version(resource: str, version: int):
    snapshot = versioning.get_snapshot(resource, version)
    return trip_service.restore_resource(resource, snapshot)
