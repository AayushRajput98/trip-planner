"""Atomic JSON file storage: one file per resource, temp-file + rename writes,
one lock per filename so concurrent requests don't interleave writes."""
import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

from .config import DATA_DIR, SEED_DIR

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(name: str) -> threading.Lock:
    with _locks_guard:
        if name not in _locks:
            _locks[name] = threading.Lock()
        return _locks[name]


def _path(name: str) -> Path:
    return Path(DATA_DIR) / name


def load_json(name: str, default: Any = None) -> Any:
    p = _path(name)
    with _lock_for(name):
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))


def ensure_seeded() -> None:
    """If DATA_DIR is a fresh, empty Volume (e.g. a brand-new Railway mount),
    populate it from the JSON files committed in the repo (SEED_DIR) so the
    app doesn't boot with a blank trip. Never overwrites a file that already
    exists, so this is safe to call on every startup, not just the first."""
    data_dir = Path(DATA_DIR)
    seed_dir = Path(SEED_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    if data_dir.resolve() == seed_dir.resolve():
        return  # local dev: DATA_DIR *is* the seed dir
    for seed_file in seed_dir.glob("*.json"):
        target = data_dir / seed_file.name
        if not target.exists():
            shutil.copy(seed_file, target)


def save_json(name: str, obj: Any) -> None:
    p = _path(name)
    with _lock_for(name):
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, p)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
