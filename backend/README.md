# Trip Planner backend

FastAPI service that owns the trip data (as JSON files) and exposes it two ways:

- **REST API** at `/api/*` — used by the static frontend (GitHub Pages).
- **MCP server** at `/mcp` — used by Claude (or any MCP-capable agent) to read and edit the
  trip directly.

Both talk to the same `app/services/trip_service.py`, so there's one source of truth.

## Run locally

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

# one-time: turn ../data-plan markdown into the JSON files under data/
# (already done in this repo — only needed again if you hand-edit trip-plan.md source)
python scripts/migrate_from_markdown.py

AUTH_TOKEN=dev-secret DATA_DIR="$(pwd)/data" uvicorn app.main:app --reload --port 8123
```

Then point the frontend's `js/config.js` `API_BASE` at `http://127.0.0.1:8123` (already the
default when the page is opened from `localhost`/`127.0.0.1`).

## Deploy to Railway

1. Create a new Railway project from this repo, root directory `backend/`.
2. **Add a Volume** and mount it at, say, `/data`. **This step is not optional** — without it,
   every redeploy wipes the trip data, since Railway's filesystem is otherwise ephemeral.
3. Set environment variables:
   - `DATA_DIR=/data` (or wherever you mounted the volume)
   - `AUTH_TOKEN=<a long random string>` — the shared secret every editor and the MCP client use
   - `ALLOWED_ORIGINS=https://<your-username>.github.io` — the GitHub Pages origin serving the
     frontend (comma-separate if you serve it from more than one origin)
4. First deploy: since the volume starts empty, copy the seed files from `backend/data/*.json`
   in this repo onto the volume once (Railway's shell, or a one-off deploy without the volume
   mounted, then move the files over) so the app doesn't start with empty data.
5. Deploy. Confirm `GET https://<your-app>.up.railway.app/health` returns `{"ok": true}`.
6. **Verify persistence**: trigger a redeploy and re-check `/api/trip` still has your data — this
   is the one step in this whole setup that silently loses everything if skipped.

## Connect the MCP server to Claude

```bash
claude mcp add --transport http trip-planner https://<your-app>.up.railway.app/mcp \
  -H "Authorization: Bearer <your AUTH_TOKEN>"
```

Once added, ask Claude to read or edit the trip — it calls the same tools listed in
`app/mcp_server.py` (get_trip, update_day, add_expense, set_timetable_status, ...), and any
change shows up on the page next time it loads `/api/trip`.

### Verify the MCP server yourself (no Claude needed)

The Streamable HTTP transport needs a three-step handshake: `initialize`, then
`notifications/initialized`, then whatever tool call you want. Swap in your host/token:

```bash
BASE=http://127.0.0.1:8123   # or your Railway URL
TOKEN=dev-secret

# 1. initialize — grabs a session id from the response headers
curl -s -D /tmp/h.txt -X POST "$BASE/mcp/" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
SID=$(grep -i mcp-session-id /tmp/h.txt | cut -d' ' -f2 | tr -d '\r')

# 2. required before any tool call
curl -s -X POST "$BASE/mcp/" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. list tools, or call one
curl -s -X POST "$BASE/mcp/" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

A request to `$BASE/mcp/` with no/wrong `Authorization` header should come back `401` — that's
the `BearerAuthASGIMiddleware` in `app/mcp_server.py` working, not a bug.

## Layout

```
app/
  main.py              FastAPI app: CORS, routers, mounts the MCP app at /mcp
  config.py            env vars: DATA_DIR, AUTH_TOKEN, ALLOWED_ORIGINS
  auth.py              shared-bearer-token dependency
  storage.py           atomic JSON file read/write
  models.py            pydantic schemas
  services/trip_service.py   all business logic (used by both routers/ and mcp_server.py)
  routers/             REST endpoints, one file per resource
  mcp_server.py         MCP tools + the auth-wrapping ASGI middleware
data/                  the live JSON files (meta/budget/days/reference/checklist/expenses)
scripts/migrate_from_markdown.py   one-off migration from the original trip-plan.md
```
