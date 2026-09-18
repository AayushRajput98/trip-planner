import os
from pathlib import Path

# Where the JSON data files live. On Railway this should point at the mounted
# Volume's path (e.g. /data) via the DATA_DIR env var — otherwise every
# redeploy wipes the trip data. Defaults to backend/data for local dev.
DATA_DIR = os.environ.get("DATA_DIR", str(Path(__file__).resolve().parents[1] / "data"))

# Shared bearer token required on every mutating REST endpoint and every MCP
# tool call. One token for the whole family — not a per-user account system.
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "dev-token-change-me")

# Comma-separated list of origins allowed to call the API (the GitHub Pages
# origin in production). "*" for local dev.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
