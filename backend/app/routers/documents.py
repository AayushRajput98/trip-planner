from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..auth import require_auth
from ..models import IdDocument
from ..services import trip_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents():
    return trip_service.list_documents()


@router.post("", dependencies=[Depends(require_auth)])
def add_document(document: IdDocument):
    entry = document.model_dump(exclude_none=True)
    entry.setdefault("uploadedAt", datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
    return trip_service.add_document(entry)


@router.delete("/{document_id}", dependencies=[Depends(require_auth)])
def delete_document(document_id: str):
    trip_service.delete_document(document_id)
    return {"ok": True}
