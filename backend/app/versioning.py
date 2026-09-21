"""Whole-file version history for every trip resource: nothing an edit
touches is ever discarded, only superseded — every write appends a snapshot
(app.services.trip_service._save) instead of only overwriting in place.
Diffing, the global feed, and per-item trash all key off the six resources
declared in app.resources.

Each resource's history lives at data/versions/<resource>.json: a plain
JSON array of {version, ts, actor, op, message, content} snapshots, oldest
first, written with the same atomic storage.save_json every other resource
file uses.
"""
from datetime import datetime, timezone
from typing import Any

from . import edit_context, storage
from .errors import NotFoundError, ValidationError
from .resources import RESOURCE_DEFAULTS, RESOURCE_FILES, RESOURCE_ID_KEY, RESOURCE_KIND

VERSIONS_DIR = "versions"


def _history_file(resource: str) -> str:
    if resource not in RESOURCE_FILES:
        raise ValidationError(f"Unknown resource: {resource!r}")
    return f"{VERSIONS_DIR}/{resource}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def record_version(resource: str, content: Any, op: str) -> dict:
    history = storage.load_json(_history_file(resource), [])
    entry = {
        "version": (history[-1]["version"] + 1) if history else 1,
        "ts": _now(),
        "actor": edit_context.current_actor(),
        "op": op,
        "message": edit_context.current_message(),
        "content": content,
    }
    history.append(entry)
    storage.save_json(_history_file(resource), history)
    return entry


def ensure_baselines() -> None:
    """Seed one "baseline" version per resource from its current content —
    but only the first time (only if that resource has no history file yet)
    — so upgrading to this feature doesn't lose the ability to restore back
    to "how it was before". Safe to call on every startup."""
    for resource, filename in RESOURCE_FILES.items():
        history_file = _history_file(resource)
        if storage.load_json(history_file, None) is not None:
            continue
        content = storage.load_json(filename, RESOURCE_DEFAULTS[resource])
        storage.save_json(history_file, [{
            "version": 1,
            "ts": _now(),
            "actor": "system",
            "op": "baseline",
            "message": None,
            "content": content,
        }])


def list_history(resource: str, limit: int | None = None) -> list[dict]:
    """Newest first, content omitted (use get_snapshot for that)."""
    history = storage.load_json(_history_file(resource), [])
    summaries = [{k: v for k, v in e.items() if k != "content"} for e in history]
    summaries.reverse()
    if limit:
        summaries = summaries[:limit]
    return summaries


def get_snapshot(resource: str, version: int) -> Any:
    history = storage.load_json(_history_file(resource), [])
    for entry in history:
        if entry["version"] == version:
            return entry["content"]
    raise NotFoundError(f"No version {version} for resource {resource!r}")


def diff(resource: str, before: Any, after: Any) -> dict:
    kind = RESOURCE_KIND[resource]
    if kind == "dict":
        before = before or {}
        after = after or {}
        added = {k: v for k, v in after.items() if k not in before}
        removed = {k: v for k, v in before.items() if k not in after}
        changed = {k: [before[k], after[k]] for k in after
                   if k in before and after[k] != before[k]}
        return {"kind": "dict", "added": added, "removed": removed, "changed": changed}

    id_key = RESOURCE_ID_KEY[resource]
    before = before or []
    after = after or []
    before_by_id = {item.get(id_key): item for item in before if isinstance(item, dict)}
    after_by_id = {item.get(id_key): item for item in after if isinstance(item, dict)}
    added = [after_by_id[i] for i in after_by_id if i not in before_by_id]
    removed = [before_by_id[i] for i in before_by_id if i not in after_by_id]
    changed = [{"id": i, "before": before_by_id[i], "after": after_by_id[i]}
               for i in after_by_id if i in before_by_id and after_by_id[i] != before_by_id[i]]
    reordered = (not added and not removed and not changed
                 and list(before_by_id) != list(after_by_id))
    return {"kind": "list", "id_key": id_key, "added": added, "removed": removed,
            "changed": changed, "reordered": reordered}


def _label(resource: str, item: dict) -> str:
    if resource == "days":
        return item.get("n") or "a day"
    if resource == "checklist":
        text = (item.get("text") or "").strip()
        return (text[:30] + "…") if len(text) > 30 else (text or "an item")
    if resource == "expenses":
        amount = item.get("amount")
        paid_by = item.get("paidBy") or "someone"
        return f"₹{amount} ({paid_by})" if amount is not None else "an expense"
    return str(item.get("id", "an item"))


def phrase(resource: str, change: dict) -> str:
    if change["kind"] == "dict":
        parts = []
        if change["added"]:
            parts.append("Added " + ", ".join(change["added"].keys()))
        if change["removed"]:
            parts.append("Removed " + ", ".join(change["removed"].keys()))
        if change["changed"]:
            parts.append("Changed " + ", ".join(change["changed"].keys()))
        return "; ".join(parts) or "No change"

    parts = []
    if change["added"]:
        parts.append("Added " + ", ".join(_label(resource, i) for i in change["added"]))
    if change["removed"]:
        parts.append("Removed " + ", ".join(_label(resource, i) for i in change["removed"]))
    if change["changed"]:
        parts.append("Changed " + ", ".join(_label(resource, c["after"]) for c in change["changed"]))
    if change["reordered"]:
        parts.append("Reordered")
    return "; ".join(parts) or "No change"


def feed(limit: int | None = None) -> list[dict]:
    """Every version across every resource, newest first. Each entry carries
    a one-line `summary` diffed against the previous version of that same
    resource."""
    entries: list[dict] = []
    for resource in RESOURCE_FILES:
        history = storage.load_json(_history_file(resource), [])
        prev_content = None
        for i, entry in enumerate(history):
            change = diff(resource, prev_content if i > 0 else None, entry["content"])
            summary = "Started tracking history" if entry["op"] == "baseline" else phrase(resource, change)
            entries.append({
                "resource": resource,
                "version": entry["version"],
                "ts": entry["ts"],
                "actor": entry["actor"],
                "op": entry["op"],
                "message": entry["message"],
                "summary": summary,
            })
            prev_content = entry["content"]
    entries.sort(key=lambda e: (e["ts"], e["version"]), reverse=True)
    if limit:
        entries = entries[:limit]
    return entries


def entry_diff(resource: str, version: int) -> dict:
    history = storage.load_json(_history_file(resource), [])
    for i, entry in enumerate(history):
        if entry["version"] == version:
            before = history[i - 1]["content"] if i > 0 else None
            return diff(resource, before, entry["content"])
    raise NotFoundError(f"No version {version} for resource {resource!r}")


def find_deleted_items(resource: str) -> list[dict]:
    """Every item that appears in some past version of `resource` but not in
    its current content — the "recently deleted" / trash view. One row per
    id, holding its last-known content and when/who removed it (the most
    recent removal, if it was deleted, restored, then deleted again)."""
    if resource not in RESOURCE_ID_KEY:
        raise ValidationError(f"{resource!r} has no per-item trash (not a collection)")
    id_key = RESOURCE_ID_KEY[resource]
    history = storage.load_json(_history_file(resource), [])
    if not history:
        return []
    current_ids = {item.get(id_key) for item in history[-1]["content"] if isinstance(item, dict)}
    deleted: dict[Any, dict] = {}
    prev_by_id: dict[Any, dict] = {}
    for entry in history:
        by_id = {item.get(id_key): item for item in entry["content"] if isinstance(item, dict)}
        for rid in set(prev_by_id) - set(by_id):
            deleted[rid] = {
                "id": rid,
                "content": prev_by_id[rid],
                "deletedAt": entry["ts"],
                "deletedBy": entry["actor"],
                "deletedInVersion": entry["version"],
            }
        prev_by_id = by_id
    return [row for rid, row in deleted.items() if rid not in current_ids]
