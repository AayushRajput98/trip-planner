import os
from pathlib import Path

# The JSON files committed in the repo (backend/data/) — always present in the
# deployed source tree regardless of where DATA_DIR points. Used to seed a
# fresh, empty Volume on first boot; see app.storage.ensure_seeded().
SEED_DIR = str(Path(__file__).resolve().parents[1] / "data")

# Where the JSON data files actually live at runtime. On Railway this should
# point at the mounted Volume's path (e.g. /data) via the DATA_DIR env var —
# otherwise every redeploy wipes the trip data. Defaults to SEED_DIR for
# local dev, where reading and writing the same directory is fine.
DATA_DIR = os.environ.get("DATA_DIR", SEED_DIR)

# Shared bearer token required on every mutating REST endpoint and every MCP
# tool call. One token for the whole family — not a per-user account system.
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "dev-token-change-me")

# Comma-separated list of origins allowed to call the API (the GitHub Pages
# origin in production). "*" for local dev.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
