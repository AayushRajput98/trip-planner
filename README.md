# Fort Country — Rajasthan trip planner

A shared, editable trip itinerary: budgets, day-by-day timetable, food/stay/fuel reference
tables, a packing checklist, and an expense log — viewable by anyone with the link, editable by
the family from the page, and editable by Claude directly through an MCP server.

## Architecture

```
index.html, css/, js/     the page — static, hosted on GitHub Pages
backend/                   FastAPI + MCP server — one Railway service
  app/                      REST API (/api/*) and MCP server (/mcp), sharing one
                             services/trip_service.py so both see the same data
  data/                     the trip's JSON files (this is what persists)
```

The page always reads from the backend's REST API. Edits happen two ways — through the page's
own edit forms, or by asking Claude, which calls the exact same backend through MCP. Either way,
there's one trip, one source of truth.

## Requirements

- **Python 3.10+** to run the backend (tested on 3.13).
- **A GitHub account** — the frontend deploys as a free GitHub Pages site from this repo.
- **A Railway account** — hosts the backend. Railway's one-time $5 trial credit does **not**
  reliably support persistent Volumes; budget for the **Hobby plan, $5/month** (which itself
  includes $5/month of usage credit), plus **$0.15/GB/month** for the Volume's storage — this
  trip's data is a few small JSON files, so that storage cost is effectively negligible. Check
  [railway.com/pricing](https://railway.com/pricing) for current numbers before committing.
- **Claude Code, or another MCP-capable client** if you want an agent editing the trip — not
  required just to view or hand-edit the page.
- No signup needed for people who only view the page.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
AUTH_TOKEN=dev-secret DATA_DIR="$(pwd)/data" uvicorn app.main:app --reload --port 8123
```

Frontend, in another terminal, from the repo root:

```bash
python -m http.server 8080
```

Open `http://127.0.0.1:8080/index.html` — `js/config.js` already points at
`http://127.0.0.1:8123` whenever the page is loaded from `localhost`/`127.0.0.1`.

## Deploying the backend (Railway)

1. Push this repo to GitHub, then create a Railway project from it with **root directory
   `backend/`**.
2. **Add a Volume and mount it (e.g. at `/data`) before your first real deploy.** This is the one
   step that isn't optional: Railway's filesystem is otherwise ephemeral, so skipping this means
   every redeploy silently wipes the whole trip.
3. Set these environment variables on the service:
   | Variable | Value |
   |---|---|
   | `DATA_DIR` | `/data` (wherever you mounted the Volume) |
   | `AUTH_TOKEN` | a long random string — the shared secret every editor and the MCP client use |
   | `ALLOWED_ORIGINS` | `https://<your-username>.github.io` (the GitHub Pages origin below) |
4. The Volume starts empty. Seed it once with the JSON files already committed under
   `backend/data/*.json` (Railway's shell, or a scratch deploy without the Volume attached, then
   move the files onto it) so the app doesn't start with a blank trip.
5. Deploy, then confirm `GET https://<your-app>.up.railway.app/health` returns `{"ok": true}`.
6. **Verify persistence before trusting it**: trigger a redeploy and re-check `/api/trip` still
   has your data.

## Deploying the frontend (GitHub Pages)

1. In the repo's GitHub Settings → Pages, deploy from the `main` branch, root.
2. Edit `js/config.js` and replace the placeholder with your real Railway URL, then commit —
   this is just a URL, not a secret, so it's fine committed to a public repo.
3. Visit `https://<your-username>.github.io/<repo>/` — it should render exactly like local dev,
   now backed by the live Railway API.

## Connecting Claude to the trip (MCP)

The backend also runs an MCP server at `/mcp` on the same Railway service, exposing 20 tools —
`get_trip`, `update_day`, `add_day`, `delete_day`, `reorder_days`, `set_timetable_status`,
`get_meta`/`update_meta`, `get_budget`/`update_budget`, `get_reference`/`update_reference`,
checklist CRUD, and expense CRUD — all backed by the same `trip_service.py` the REST API uses,
so nothing an agent does can drift from what the page shows.

```bash
claude mcp add --transport http trip-planner https://<your-app>.up.railway.app/mcp \
  -H "Authorization: Bearer <your AUTH_TOKEN>"
```

Then just ask, in a normal conversation: "mark Day 3's fort visit as visited", "add a ₹2,000
fuel expense paid by Mum", "add a new day after Day 5 for Jodhpur". Every tool call requires the
same shared token as the page's own edits (checked by a small ASGI middleware in front of the
MCP app — see `backend/app/mcp_server.py`), and every change is visible on the page the next
time it loads.

To verify the server yourself without Claude, `backend/README.md` has the raw MCP handshake
(`initialize` → `notifications/initialized` → `tools/call`) as curl commands.

## Editing the trip

- **On the page**: open Settings, paste the shared editor token and your name, then use the
  "Edit ..." buttons throughout. Deeply nested fields (a day's full timetable/alerts/logistics,
  the reference tables) are edited as raw JSON rather than bespoke forms for every field — most
  editing is expected to happen by asking Claude through MCP, so that's where the form-building
  effort went instead.
- **Visited/skipped tracking**: each timetable entry has a small pill you click to cycle
  planned → visited → skipped.
- **Expenses**: logged flatly (date, amount, who paid, category, note) with a running total per
  payer, in the Expenses section.

## Repo layout

See `backend/README.md` for the backend's internal layout (routers, services, storage, the MCP
server) in more detail.

## What happened to the old static page

`trip-plan-static.html` is the original single-file prototype this project grew out of (all
data hardcoded in a `<script>` block, no backend, no MCP). It's kept only as a frozen reference —
the live site is `index.html` + `backend/`.
