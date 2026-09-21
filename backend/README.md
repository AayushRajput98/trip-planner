# Trip Planner backend

FastAPI service that owns the trip data (as JSON files) and exposes it two ways:

- **REST API** at `/api/*` — used by the static frontend (GitHub Pages), gated by the shared
  `AUTH_TOKEN` bearer secret for writes.
- **MCP server** at `/mcp` — used by Claude (Code, Desktop, mobile, web) or ChatGPT to read and
  edit the trip directly, gated by real OAuth 2.1 (`app/oauth/provider.py`). Desktop/mobile/
  ChatGPT's "Add custom connector" flow only understands OAuth, not a static header — see that
  module's docstring for how the "login" step maps onto the one shared secret.

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

Run the test suite with `pytest` from `backend/` — it never touches `data/`, each test gets its
own throwaway temp directory.

## Deploy to Railway

1. Create a new Railway project from this repo, root directory `backend/`.
2. **Add a Volume** and mount it at, say, `/data`. **This step is not optional** — without it,
   every redeploy wipes the trip data, since Railway's filesystem is otherwise ephemeral.
3. Set environment variables:
   - `DATA_DIR=/data` (or wherever you mounted the volume)
   - `AUTH_TOKEN=<a long random string>` — the shared secret used for page edits, and the
     "password" typed into the MCP `/consent` page when approving a new client
   - `ALLOWED_ORIGINS=https://<your-username>.github.io` — the GitHub Pages origin serving the
     frontend (comma-separate if you serve it from more than one origin)
   - `PUBLIC_BASE_URL=https://<your-app>.up.railway.app` — this service's own public URL, used
     as the MCP OAuth issuer/resource identifier. **Must be the real `https://` URL** — the OAuth
     handshake breaks if this doesn't match what clients actually connect to.
4. Deploy. **The Volume auto-seeds itself** — `app/main.py` calls `storage.ensure_seeded()` on
   every boot, which copies the JSON files committed under `backend/data/*.json` into `DATA_DIR`
   for any file that isn't already there. It never overwrites a file that already exists, so it
   only does anything the first time (an empty Volume) and is a no-op on every later redeploy.
   No manual shell step needed.
5. Confirm `GET https://<your-app>.up.railway.app/health` returns `{"ok": true}`.
6. **Verify persistence**: trigger a redeploy and re-check `/api/trip` still has your data — this
   is the one step in this whole setup that silently loses everything if skipped.

## Connect the MCP server

**Claude Desktop, the Claude mobile app, claude.ai, or ChatGPT**: add a custom connector with
the URL `https://<your-app>.up.railway.app/mcp`. It'll redirect you to a plain page on this
server ("Approve access for `<client name>`?") asking for the shared secret — that's
`AUTH_TOKEN`, the same one used for page edits. Approve once per device/app; the client then
holds a token that auto-refreshes, so this isn't a repeat-every-time login.

**Claude Code** (custom headers aren't needed anymore, but still work — this is just a normal
OAuth-capable HTTP MCP server now):
```bash
claude mcp add --transport http trip-planner https://<your-app>.up.railway.app/mcp
```

Once connected, ask Claude/ChatGPT to read or edit the trip — it calls the same tools listed in
`app/mcp_server.py` (get_trip, update_day, add_expense, set_timetable_status, ...), and any
change shows up on the page next time it loads `/api/trip`.

### Verify the OAuth flow yourself (no Claude/ChatGPT needed)

```bash
BASE=http://127.0.0.1:8123   # or your Railway URL
SECRET=dev-secret            # your AUTH_TOKEN

# 1. register a client (RFC 7591 — what Desktop/ChatGPT do automatically)
curl -s -X POST "$BASE/register" -H "Content-Type: application/json" -d '{
  "redirect_uris": ["http://localhost:9999/callback"], "client_name": "test",
  "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
  "token_endpoint_auth_method": "none"}'
# -> note client_id

# 2. build a PKCE pair, then hit /authorize — it 302s to /consent?txn=...
VERIFIER=$(python3 -c "import secrets;print(secrets.token_urlsafe(64))")
CHALLENGE=$(python3 -c "import hashlib,base64;print(base64.urlsafe_b64encode(hashlib.sha256('$VERIFIER'.encode()).digest()).decode().rstrip('='))")
curl -s -D - -o /dev/null "$BASE/authorize?client_id=<client_id>&redirect_uri=http://localhost:9999/callback&response_type=code&code_challenge=$CHALLENGE&code_challenge_method=S256" | grep -i location
# -> note the txn= value

# 3. "approve" it the way the consent page's form does
curl -s -D - -o /dev/null -X POST "$BASE/consent" -d "txn=<txn>&secret=$SECRET" | grep -i location
# -> note the code= value from the redirect

# 4. exchange the code for tokens
curl -s -X POST "$BASE/token" -d "grant_type=authorization_code&code=<code>&redirect_uri=http://localhost:9999/callback&client_id=<client_id>&code_verifier=$VERIFIER"
```

The resulting `access_token` is a normal `Authorization: Bearer` value for the Streamable HTTP
transport (`initialize` → `notifications/initialized` → `tools/call`, same three-step handshake
as any MCP HTTP server). No `Authorization` header, or a garbage one, should 401.

## Layout

```
app/
  main.py              FastAPI app: CORS, routers, mounts the MCP+OAuth app at the root
  config.py            env vars: DATA_DIR, AUTH_TOKEN, ALLOWED_ORIGINS, PUBLIC_BASE_URL
  auth.py              shared-bearer-token dependency (REST API writes) + check_token() helper;
                       also captures X-Editor-Name/X-Edit-Message into edit_context per request
  edit_context.py      who's editing + their optional note, for the duration of one request/tool
                       call — read by versioning.record_version so trip_service doesn't need an
                       actor/message parameter threaded through every function
  errors.py            NotFoundError/ValidationError, shared by trip_service and versioning
  resources.py         the six resource names <-> their JSON files, kind (dict/list), id key
  versioning.py        version history: record/list/diff/restore a resource, "recently deleted"
                       trash for the three collections (days/checklist/expenses)
  storage.py           atomic JSON file read/write, ensure_seeded() for a fresh Volume
  models.py            pydantic schemas
  services/trip_service.py   all business logic (used by both routers/ and mcp_server.py) — every
                       write goes through _save(), which also calls versioning.record_version
  routers/             REST endpoints, one file per resource, plus versions.py (history/restore)
  mcp_server.py         MCP tools + OAuth wiring (AuthSettings, the /consent custom route)
  oauth/provider.py     the OAuth authorization server: clients/codes/tokens, the /consent page
data/                  the live JSON files (meta/budget/days/reference/checklist/expenses/oauth_*)
data/versions/         one JSON array per resource: every past version, never trimmed
scripts/migrate_from_markdown.py   one-off migration from the original trip-plan.md
tests/                 pytest — versioning.py/trip_service directly, plus an HTTP smoke test
                       through the real FastAPI app (run with `pytest` from backend/)
```
