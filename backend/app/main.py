from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ALLOWED_ORIGINS
from .mcp_server import build_mcp_inner_app
from .routers import budget, checklist, days, expenses, meta, reference, trip
from .services.trip_service import NotFoundError, ValidationError
from .storage import ensure_seeded

# On a brand-new Railway Volume (or any empty DATA_DIR), populate it from the
# JSON files committed in the repo before anything tries to read from it.
ensure_seeded()

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


@app.get("/health")
def health():
    return {"ok": True}


# Mounted at the root, registered last so /api/* and /health above still win
# first for their exact paths — this carries /mcp itself plus the OAuth
# routes (/authorize, /token, /register, /.well-known/oauth-authorization-
# server, /consent). See mcp_server.build_mcp_inner_app's docstring for why
# this can't be a /mcp sub-mount instead.
app.mount("/", mcp_inner_app)
