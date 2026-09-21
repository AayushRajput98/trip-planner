"""Canonical resource names, their backing JSON files, and enough shape info
(kind, id key) for versioning.py to diff, describe, and trash-scan generically
without hardcoding six near-identical branches everywhere."""

RESOURCE_FILES = {
    "meta": "meta.json",
    "budget": "budget.json",
    "days": "days.json",
    "reference": "reference.json",
    "checklist": "checklist.json",
    "expenses": "expenses.json",
}

RESOURCE_DEFAULTS = {
    "meta": {},
    "budget": {},
    "days": [],
    "reference": {},
    "checklist": [],
    "expenses": [],
}

# "dict" resources diff by top-level key; "list" resources diff by item id.
RESOURCE_KIND = {
    "meta": "dict",
    "budget": "dict",
    "reference": "dict",
    "days": "list",
    "checklist": "list",
    "expenses": "list",
}

# Only collections (list-kind resources) support per-item trash/restore.
RESOURCE_ID_KEY = {
    "days": "n",
    "checklist": "id",
    "expenses": "id",
}
