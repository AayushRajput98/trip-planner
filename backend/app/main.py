from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ALLOWED_ORIGINS, DATA_DIR
from .errors import NotFoundError, ValidationError
from .mcp_server import build_mcp_inner_app
from .routers import bookings, budget, checklist, days, documents, expenses, meta, reference, trip, uploads, versions
from .storage import ensure_seeded
from .versioning import ensure_baselines

# On a brand-new Railway Volume (or any empty DATA_DIR), populate it from the
# JSON files committed in the repo before anything tries to read from it.
ensure_seeded()
# Seed one "baseline" version per resource so history/restore always has a
# starting point, even for data that existed before this feature shipped.
ensure_baselines()

# Mounting a Starlette sub-app does NOT forward ASGI "lifespan" events to it,
# and the MCP session manager only starts inside its own lifespan context —
# so we build the inner app once here and manually enter its lifespan from
# FastAPI's own, keeping it alive for the whole process.
mcp_inner_app = build_mcp_inner_app()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp_inner_app.router.lifespan_context(mcp_inner_app):
        yield


app = FastAPI(title="Trip Planner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
def handle_not_found(_request: Request, exc: NotFoundError):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(ValidationError)
def handle_validation(_request: Request, exc: ValidationError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


app.include_router(trip.router)
app.include_router(meta.router)
app.include_router(budget.router)
app.include_router(days.router)
app.include_router(reference.router)
app.include_router(checklist.router)
app.include_router(expenses.router)
app.include_router(bookings.router)
app.include_router(documents.router)
app.include_router(uploads.router)
app.include_router(versions.router)


@app.get("/health")
def health():
    return {"ok": True}


# Uploaded receipts/ID photos (app.routers.uploads writes here). Registered
# before the root MCP mount below for the same reason /api/* is — Starlette
# matches mounts in registration order, so this has to win over "/" for any
# /uploads/* path.
_uploads_dir = Path(DATA_DIR) / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# Mounted at the root, registered last so /api/*, /health and /uploads above
# still win first for their exact paths — this carries /mcp itself plus the
# OAuth routes (/authorize, /token, /register, /.well-known/oauth-authorization-
# server, /consent). See mcp_server.build_mcp_inner_app's docstring for why
# this can't be a /mcp sub-mount instead.
app.mount("/", mcp_inner_app)
