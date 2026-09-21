import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Must happen before any `app.*` module is imported anywhere in the test
# session: app.config reads DATA_DIR from the environment at import time, and
# tests must never touch the real committed data under backend/data/. Each
# test additionally gets its own tmp_path via the isolated_data_dir fixture
# below, which takes priority once it's active.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="trip-planner-tests-"))
os.environ.setdefault("AUTH_TOKEN", "test-token")

import pytest  # noqa: E402

from app import storage  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Every test gets a private, empty data directory — storage.DATA_DIR is
    looked up dynamically on every call, so this fully isolates one test's
    writes from the next without needing to reload any app module."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    yield tmp_path
