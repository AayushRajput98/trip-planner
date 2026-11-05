"""Generic file upload used by Bookings (hotel receipts) and the per-person
ID document shelf. Stores the file on disk under DATA_DIR/uploads with a
random name (the original filename is kept only as display text, never as
the path, so it can't be used to overwrite or traverse elsewhere) and hands
back an absolute URL served by the StaticFiles mount in app.main."""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from ..auth import require_auth
from ..config import DATA_DIR, PUBLIC_BASE_URL

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_DIR = Path(DATA_DIR) / "uploads"
MAX_BYTES = 15 * 1024 * 1024  # 15 MB — plenty for a photographed receipt or ID


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix or "") else ""


def store_upload(data: bytes, filename: str) -> dict:
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is larger than 15 MB")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{_safe_suffix(filename)}"
    (UPLOAD_DIR / stored_name).write_bytes(data)
    return {"url": f"{PUBLIC_BASE_URL}/uploads/{stored_name}", "name": filename or stored_name}


@router.post("", dependencies=[Depends(require_auth)])
async def upload_file(file: UploadFile):
    data = await file.read()
    return store_upload(data, file.filename or "")
