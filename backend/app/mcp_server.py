"""MCP server exposing the trip data to agents (Claude, ChatGPT, ...).

Every tool here is a thin wrapper around app.services.trip_service — the
exact same logic the REST routers use, so the page and any agent editing
through MCP always see a consistent trip.

Built on mcp>=2.0's MCPServer (the v2 rename of FastMCP). Mounted as an ASGI
app at /mcp by app.main, wrapped in BearerAuthASGIMiddleware so every call
requires the same shared Authorization: Bearer <token> the REST API uses.
"""
from typing import Any

from mcp.server.mcpserver import MCPServer
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .auth import check_token
from .services import trip_service

mcp = MCPServer(
    "trip-planner",
    instructions=(
        "Tools for reading and editing a family road-trip itinerary: trip meta, budget "
        "config, day-by-day timetable (with a planned/visited/skipped status per stop), "
        "food/stay/fuel/variant/notes reference tables, a packing checklist, and an "
        "expense log. Call get_trip() first to see the whole plan before editing."
    ),
)


@mcp.tool()
def get_trip() -> dict:
    """Return the entire trip: meta, budget, all days, reference tables, checklist."""
    return trip_service.get_trip()


@mcp.tool()
def get_day(n: str) -> dict:
    """Get one day by its id, e.g. 'Day 1' or 'Return'."""
    return trip_service.get_day(n)


@mcp.tool()
def update_day(n: str, patch: dict[str, Any]) -> dict:
    """Merge `patch` into the day with id `n` (e.g. {"title": "..."} or
    {"tl": [...]} to replace the whole timetable). Only given keys change."""
    return trip_service.update_day(n, patch)


@mcp.tool()
def add_day(day: dict[str, Any]) -> dict:
    """Append a new day. Must include a unique "n" (e.g. "Day 9")."""
    return trip_service.add_day(day)


@mcp.tool()
def delete_day(n: str) -> dict:
    """Remove the day with id `n`."""
    trip_service.delete_day(n)
    return {"ok": True}


@mcp.tool()
def reorder_days(order: list[str]) -> list[dict]:
    """Reorder days. `order` must list every existing day id exactly once."""
    return trip_service.reorder_days(order)


@mcp.tool()
def set_timetable_status(day_n: str, index: int, status: str) -> dict:
    """Mark one timetable entry (by its 0-based index within that day) as
    "planned", "visited", or "skipped"."""
    return trip_service.set_timetable_status(day_n, index, status)


@mcp.tool()
def get_meta() -> dict:
    """Get the trip title, kicker, subtitle and headline pills."""
    return trip_service.get_meta()


@mcp.tool()
def update_meta(patch: dict[str, Any]) -> dict:
    """Merge `patch` into the trip meta (title/kicker/sub/pills)."""
    return trip_service.update_meta(patch)


@mcp.tool()
def get_budget() -> dict:
    """Get vehicle options, fuel prices, and the budget calculator's defaults."""
    return trip_service.get_budget()


@mcp.tool()
def update_budget(patch: dict[str, Any]) -> dict:
    """Merge `patch` into the budget config (vehicle/prices/legs)."""
    return trip_service.update_budget(patch)


@mcp.tool()
def get_reference(section: str) -> Any:
    """Get one reference section: food, stays, fuelStops, variants, notes,
    sources, photoUrls, or photoWiki."""
    return trip_service.get_reference(section)


@mcp.tool()
def update_reference(section: str, data: Any) -> Any:
    """Replace one reference section wholesale with `data`. `section` is one
    of: food, stays, fuelStops, variants, notes, sources, photoUrls, photoWiki."""
    return trip_service.update_reference(section, data)


@mcp.tool()
def get_checklist() -> list[dict]:
    """Get the packing checklist."""
    return trip_service.get_checklist()


@mcp.tool()
def add_checklist_item(text: str) -> dict:
    """Add a new packing checklist item."""
    return trip_service.add_checklist_item(text)


@mcp.tool()
def set_checklist_item_done(item_id: str, done: bool) -> dict:
    """Tick or untick a checklist item by its id."""
    return trip_service.set_checklist_item(item_id, {"done": done})


@mcp.tool()
def remove_checklist_item(item_id: str) -> dict:
    """Remove a checklist item by its id."""
    trip_service.remove_checklist_item(item_id)
    return {"ok": True}


@mcp.tool()
def list_expenses(paid_by: str | None = None, day_ref: str | None = None) -> list[dict]:
    """List logged expenses, optionally filtered by who paid or which day."""
    return trip_service.list_expenses(paid_by=paid_by, day_ref=day_ref)


@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    paidBy: str,
    currency: str = "INR",
    category: str | None = None,
    note: str | None = None,
    dayRef: str | None = None,
) -> dict:
    """Log an expense: date (YYYY-MM-DD), amount, who paid, and optionally
    currency, a category, a note, and which day it belongs to."""
    entry = {"date": date, "amount": amount, "paidBy": paidBy, "currency": currency}
    if category is not None:
        entry["category"] = category
    if note is not None:
        entry["note"] = note
    if dayRef is not None:
        entry["dayRef"] = dayRef
    return trip_service.add_expense(entry)


@mcp.tool()
def delete_expense(expense_id: str) -> dict:
    """Delete a logged expense by its id."""
    trip_service.delete_expense(expense_id)
    return {"ok": True}


class BearerAuthASGIMiddleware:
    """Wraps the MCP Starlette app so every request needs the same shared
    Authorization: Bearer <token> the REST API's write endpoints require.
    Non-"http" scopes (e.g. "lifespan") pass straight through untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            raw = headers.get(b"authorization", b"").decode("latin-1")
            token = raw[len("Bearer "):].strip() if raw.startswith("Bearer ") else None
            if not check_token(token):
                response = JSONResponse({"detail": "Missing or invalid bearer token"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def build_mcp_inner_app():
    """The raw MCP Starlette app (unwrapped). Its `.router.lifespan_context`
    must be entered by the parent FastAPI app's own lifespan — mounting a
    sub-app does NOT forward lifespan events to it, and the MCP session
    manager only starts inside that lifespan. See app/main.py.

    `host="0.0.0.0"` (matching how uvicorn actually binds) is required here:
    the SDK auto-enables DNS-rebinding protection — rejecting any request
    whose Host header isn't localhost/127.0.0.1 — whenever this defaults to
    "127.0.0.1". That's fine talking to it on localhost, but it 401s every
    request once deployed behind a real hostname (e.g. Railway). Our own
    BearerAuthASGIMiddleware is the auth boundary we actually rely on."""
    return mcp.streamable_http_app(streamable_http_path="/", host="0.0.0.0")
