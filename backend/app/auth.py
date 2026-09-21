from urllib.parse import unquote

from fastapi import Header, HTTPException, status

from . import edit_context
from .config import AUTH_TOKEN


def check_token(token: str | None) -> bool:
    return bool(token) and token == AUTH_TOKEN


async def require_auth(
    authorization: str | None = Header(default=None),
    x_editor_name: str | None = Header(default=None, alias="X-Editor-Name"),
    x_edit_message: str | None = Header(default=None, alias="X-Edit-Message"),
) -> None:
    """FastAPI dependency for every mutating REST route: checks the shared
    bearer token, then makes who's editing (and their optional note) visible
    to trip_service._save -> versioning.record_version for the rest of this
    request via edit_context.

    Must stay `async def` and must NOT be a "yield" dependency: a sync
    dependency (or the cleanup half of a yield one) runs in FastAPI's worker
    threadpool, each call getting an unrelated copy of the context, so a
    plain `.set()` here wouldn't be visible to the route handler's own
    (separately offloaded) execution. An async function runs inline in the
    request's real task/context instead, so its writes ARE visible to
    whatever FastAPI offloads afterwards. See app/edit_context.py."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):].strip()
    if not check_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid bearer token")
    edit_context.set_actor(x_editor_name or "Unknown editor")
    # api.js percent-encodes this (header values must stay ASCII-safe).
    edit_context.set_message(unquote(x_edit_message) if x_edit_message else None)
