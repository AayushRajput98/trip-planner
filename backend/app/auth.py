from fastapi import Header, HTTPException, status

from .config import AUTH_TOKEN


def check_token(token: str | None) -> bool:
    return bool(token) and token == AUTH_TOKEN


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency for every mutating REST route."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):].strip()
    if not check_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid bearer token")
