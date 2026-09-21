"""All trip business logic. Both the REST routers and the MCP tools call only
this module, so there is exactly one implementation of every read/write path."""
import uuid
from typing import Any

from .. import storage, versioning
from ..errors import NotFoundError, ValidationError
from ..resources import RESOURCE_FILES

META_FILE = RESOURCE_FILES["meta"]
BUDGET_FILE = RESOURCE_FILES["budget"]
DAYS_FILE = RESOURCE_FILES["days"]
REFERENCE_FILE = RESOURCE_FILES["reference"]
CHECKLIST_FILE = RESOURCE_FILES["checklist"]
EXPENSES_FILE = RESOURCE_FILES["expenses"]

REFERENCE_SECTIONS = {"food", "stays", "fuelStops", "variants", "notes", "sources", "photoUrls", "photoWiki"}


def _save(resource: str, filename: str, obj: Any, op: str) -> None:
    """Write `obj` as the resource's new current content, then record it as
    a new version — the single chokepoint every mutation in this module goes
    through, so nothing ever just overwrites history away."""
    storage.save_json(filename, obj)
    versioning.record_version(resource, obj, op)


def _merge_patch(target: dict, patch: dict, protected_keys: set[str] = frozenset()) -> None:
    """RFC 7396 JSON Merge Patch, in place: a `null` value deletes the key
    instead of storing a literal null. Without this, a patch can add a field
    but never remove one — every mistaken or exploratory key becomes
    permanent. `protected_keys` (e.g. a record's own id) are left completely
    untouched by a null in the patch — not deleted, and not overwritten to
    null either."""
    for key, val in patch.items():
        if key in protected_keys and val is None:
            continue
        if val is None:
            target.pop(key, None)
        else:
            target[key] = val


# ---- meta ---------------------------------------------------------------
def get_meta() -> dict:
    return storage.load_json(META_FILE, {})


def update_meta(patch: dict) -> dict:
    meta = get_meta()
    _merge_patch(meta, patch)
    _save("meta", META_FILE, meta, "update_meta")
    return meta


# ---- budget ---------------------------------------------------------------
def get_budget() -> dict:
    return storage.load_json(BUDGET_FILE, {})


def update_budget(patch: dict) -> dict:
    budget = get_budget()
    for key, val in patch.items():
        if key == "prices" and isinstance(val, dict) and isinstance(budget.get("prices"), dict):
            prices = budget["prices"]
            defaults_patch = val.pop("defaults", None)
            _merge_patch(prices, val)
            if defaults_patch and isinstance(prices.get("defaults"), dict):
                _merge_patch(prices["defaults"], defaults_patch)
            elif defaults_patch:
                prices["defaults"] = defaults_patch
        elif val is None:
            budget.pop(key, None)
        else:
            budget[key] = val
    _save("budget", BUDGET_FILE, budget, "update_budget")
    return budget


# ---- days ---------------------------------------------------------------
def list_days() -> list[dict]:
    return storage.load_json(DAYS_FILE, [])


def _find_day_index(days: list[dict], n: str) -> int:
    for i, d in enumerate(days):
        if d.get("n") == n:
            return i
    raise NotFoundError(f"No day with n={n!r}")


def get_day(n: str) -> dict:
    days = list_days()
    return days[_find_day_index(days, n)]


def add_day(day: dict, op: str = "add_day") -> dict:
    days = list_days()
    if any(d.get("n") == day.get("n") for d in days):
        raise ValidationError(f"A day with n={day.get('n')!r} already exists")
    for entry in day.get("tl", []):
        entry.setdefault("status", "planned")
    days.append(day)
    _save("days", DAYS_FILE, days, op)
    return day


def update_day(n: str, patch: dict) -> dict:
    days = list_days()
    idx = _find_day_index(days, n)
    day = days[idx]
    if "tl" in patch:
        for entry in patch["tl"]:
            entry.setdefault("status", "planned")
    _merge_patch(day, patch, protected_keys={"n"})
    days[idx] = day
    _save("days", DAYS_FILE, days, "update_day")
    return day


def delete_day(n: str) -> None:
    days = list_days()
    idx = _find_day_index(days, n)
    days.pop(idx)
    _save("days", DAYS_FILE, days, "delete_day")


def reorder_days(order: list[str]) -> list[dict]:
    days = list_days()
    by_n = {d["n"]: d for d in days}
    if set(order) != set(by_n.keys()):
        raise ValidationError("reorder_days: the given order must contain exactly the existing day ids")
    new_days = [by_n[n] for n in order]
    _save("days", DAYS_FILE, new_days, "reorder_days")
    return new_days


def set_timetable_status(day_n: str, index: int, status: str) -> dict:
    if status not in ("planned", "visited", "skipped"):
        raise ValidationError(f"Invalid status: {status!r}")
    days = list_days()
    idx = _find_day_index(days, day_n)
    day = days[idx]
    tl = day.get("tl", [])
    if index < 0 or index >= len(tl):
        raise NotFoundError(f"No timetable entry {index} on day {day_n!r}")
    tl[index]["status"] = status
    _save("days", DAYS_FILE, days, "set_timetable_status")
    return day


# ---- reference (food/stays/fuelStops/variants/notes/sources/photos) -------
def get_reference(section: str) -> Any:
    if section not in REFERENCE_SECTIONS:
        raise ValidationError(f"Unknown reference section: {section!r}")
    ref = storage.load_json(REFERENCE_FILE, {})
    return ref.get(section)


def update_reference(section: str, data: Any) -> Any:
    if section not in REFERENCE_SECTIONS:
        raise ValidationError(f"Unknown reference section: {section!r}")
    ref = storage.load_json(REFERENCE_FILE, {})
    ref[section] = data
    _save("reference", REFERENCE_FILE, ref, "update_reference")
    return data


def get_full_reference() -> dict:
    return storage.load_json(REFERENCE_FILE, {})


# ---- checklist ------------------------------------------------------------
def get_checklist() -> list[dict]:
    return storage.load_json(CHECKLIST_FILE, [])


def add_checklist_item(text: str) -> dict:
    items = get_checklist()
    item = {"id": uuid.uuid4().hex[:8], "text": text, "done": False}
    items.append(item)
    _save("checklist", CHECKLIST_FILE, items, "add_checklist_item")
    return item


def set_checklist_item(item_id: str, patch: dict) -> dict:
    items = get_checklist()
    for item in items:
        if item["id"] == item_id:
            item.update(patch)
            _save("checklist", CHECKLIST_FILE, items, "set_checklist_item")
            return item
    raise NotFoundError(f"No checklist item {item_id!r}")


def remove_checklist_item(item_id: str) -> None:
    items = get_checklist()
    new_items = [i for i in items if i["id"] != item_id]
    if len(new_items) == len(items):
        raise NotFoundError(f"No checklist item {item_id!r}")
    _save("checklist", CHECKLIST_FILE, new_items, "remove_checklist_item")


def restore_checklist_item(item: dict) -> dict:
    """Re-insert a full checklist item dict (from trash), preserving its
    original id — add_checklist_item always mints a fresh one."""
    items = get_checklist()
    if any(i["id"] == item["id"] for i in items):
        raise ValidationError(f"Checklist item {item['id']!r} already exists")
    items.append(item)
    _save("checklist", CHECKLIST_FILE, items, "restore_item")
    return item


# ---- expenses ---------------------------------------------------------------
def list_expenses(paid_by: str | None = None, day_ref: str | None = None) -> list[dict]:
    expenses = storage.load_json(EXPENSES_FILE, [])
    if paid_by:
        expenses = [e for e in expenses if e.get("paidBy") == paid_by]
    if day_ref:
        expenses = [e for e in expenses if e.get("dayRef") == day_ref]
    return expenses


def add_expense(entry: dict, op: str = "add_expense") -> dict:
    expenses = storage.load_json(EXPENSES_FILE, [])
    entry = dict(entry)
    entry["id"] = entry.get("id") or uuid.uuid4().hex[:8]
    if any(e["id"] == entry["id"] for e in expenses):
        raise ValidationError(f"Expense {entry['id']!r} already exists")
    expenses.append(entry)
    _save("expenses", EXPENSES_FILE, expenses, op)
    return entry


def delete_expense(expense_id: str) -> None:
    expenses = storage.load_json(EXPENSES_FILE, [])
    new_expenses = [e for e in expenses if e["id"] != expense_id]
    if len(new_expenses) == len(expenses):
        raise NotFoundError(f"No expense {expense_id!r}")
    _save("expenses", EXPENSES_FILE, new_expenses, "delete_expense")


# ---- restore ---------------------------------------------------------------
def restore_resource(resource: str, content: Any) -> Any:
    """Write `content` (typically a past version's snapshot) as the new
    current state for `resource`, through the same versioned save path as
    any other edit — a whole-file restore is just another version, not a
    special case."""
    if resource not in RESOURCE_FILES:
        raise ValidationError(f"Unknown resource: {resource!r}")
    _save(resource, RESOURCE_FILES[resource], content, "restore")
    return content


# ---- aggregate --------------------------------------------------------------
def get_trip() -> dict:
    """Everything render.js needs in one call, shaped like the original
    hardcoded TRIP object from the static-page prototype."""
    budget = get_budget()
    ref = get_full_reference()
    return {
        "meta": get_meta(),
        "vehicle": budget.get("vehicle", []),
        "prices": budget.get("prices", {}),
        "legs": budget.get("legs", []),
        "days": list_days(),
        "food": ref.get("food", []),
        "stays": ref.get("stays", []),
        "fuelStops": ref.get("fuelStops", []),
        "variants": ref.get("variants", []),
        "notes": ref.get("notes", []),
        "sources": ref.get("sources", []),
        "photoUrls": ref.get("photoUrls", {}),
        "photoWiki": ref.get("photoWiki", {}),
        "checklist": get_checklist(),
    }
