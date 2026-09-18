"""All trip business logic. Both the REST routers and the MCP tools call only
this module, so there is exactly one implementation of every read/write path."""
import uuid
from typing import Any

from .. import storage

META_FILE = "meta.json"
BUDGET_FILE = "budget.json"
DAYS_FILE = "days.json"
REFERENCE_FILE = "reference.json"
CHECKLIST_FILE = "checklist.json"
EXPENSES_FILE = "expenses.json"

REFERENCE_SECTIONS = {"food", "stays", "fuelStops", "variants", "notes", "sources", "photoUrls", "photoWiki"}


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


# ---- meta ---------------------------------------------------------------
def get_meta() -> dict:
    return storage.load_json(META_FILE, {})


def update_meta(patch: dict) -> dict:
    meta = get_meta()
    meta.update(patch)
    storage.save_json(META_FILE, meta)
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
            prices.update(val)
            if defaults_patch and isinstance(prices.get("defaults"), dict):
                prices["defaults"].update(defaults_patch)
            elif defaults_patch:
                prices["defaults"] = defaults_patch
        else:
            budget[key] = val
    storage.save_json(BUDGET_FILE, budget)
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


def add_day(day: dict) -> dict:
    days = list_days()
    if any(d.get("n") == day.get("n") for d in days):
        raise ValidationError(f"A day with n={day.get('n')!r} already exists")
    for entry in day.get("tl", []):
        entry.setdefault("status", "planned")
    days.append(day)
    storage.save_json(DAYS_FILE, days)
    return day


def update_day(n: str, patch: dict) -> dict:
    days = list_days()
    idx = _find_day_index(days, n)
    day = days[idx]
    if "tl" in patch:
        for entry in patch["tl"]:
            entry.setdefault("status", "planned")
    day.update(patch)
    days[idx] = day
    storage.save_json(DAYS_FILE, days)
    return day


def delete_day(n: str) -> None:
    days = list_days()
    idx = _find_day_index(days, n)
    days.pop(idx)
    storage.save_json(DAYS_FILE, days)


def reorder_days(order: list[str]) -> list[dict]:
    days = list_days()
    by_n = {d["n"]: d for d in days}
    if set(order) != set(by_n.keys()):
        raise ValidationError("reorder_days: the given order must contain exactly the existing day ids")
    new_days = [by_n[n] for n in order]
    storage.save_json(DAYS_FILE, new_days)
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
    storage.save_json(DAYS_FILE, days)
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
    storage.save_json(REFERENCE_FILE, ref)
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
    storage.save_json(CHECKLIST_FILE, items)
    return item


def set_checklist_item(item_id: str, patch: dict) -> dict:
    items = get_checklist()
    for item in items:
        if item["id"] == item_id:
            item.update(patch)
            storage.save_json(CHECKLIST_FILE, items)
            return item
    raise NotFoundError(f"No checklist item {item_id!r}")


def remove_checklist_item(item_id: str) -> None:
    items = get_checklist()
    new_items = [i for i in items if i["id"] != item_id]
    if len(new_items) == len(items):
        raise NotFoundError(f"No checklist item {item_id!r}")
    storage.save_json(CHECKLIST_FILE, new_items)


# ---- expenses ---------------------------------------------------------------
def list_expenses(paid_by: str | None = None, day_ref: str | None = None) -> list[dict]:
    expenses = storage.load_json(EXPENSES_FILE, [])
    if paid_by:
        expenses = [e for e in expenses if e.get("paidBy") == paid_by]
    if day_ref:
        expenses = [e for e in expenses if e.get("dayRef") == day_ref]
    return expenses


def add_expense(entry: dict) -> dict:
    expenses = storage.load_json(EXPENSES_FILE, [])
    entry = dict(entry)
    entry["id"] = entry.get("id") or uuid.uuid4().hex[:8]
    expenses.append(entry)
    storage.save_json(EXPENSES_FILE, expenses)
    return entry


def delete_expense(expense_id: str) -> None:
    expenses = storage.load_json(EXPENSES_FILE, [])
    new_expenses = [e for e in expenses if e["id"] != expense_id]
    if len(new_expenses) == len(expenses):
        raise NotFoundError(f"No expense {expense_id!r}")
    storage.save_json(EXPENSES_FILE, new_expenses)


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
