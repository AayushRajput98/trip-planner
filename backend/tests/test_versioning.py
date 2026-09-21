"""Core versioning behavior, exercised directly against trip_service and
versioning (no HTTP/MCP layer) — the same functions both surfaces call
through, so this is where the actual save-a-version-instead-of-destroying
logic gets proven out."""
import pytest

from app import edit_context, storage, versioning
from app.errors import ValidationError
from app.services import trip_service


def test_write_records_version_with_actor_and_message():
    with edit_context.editing(actor="Mum", message="fix the title"):
        trip_service.update_meta({"title": "New Title"})

    history = versioning.list_history("meta")
    assert len(history) == 1
    entry = history[0]
    assert entry["version"] == 1
    assert entry["actor"] == "Mum"
    assert entry["message"] == "fix the title"
    assert entry["op"] == "update_meta"


def test_write_without_context_falls_back_to_unknown_actor():
    trip_service.update_meta({"title": "No editor set"})
    entry = versioning.list_history("meta")[0]
    assert entry["actor"] == "Unknown"
    assert entry["message"] is None


def test_diff_and_phrase_dict_resource():
    before = {"title": "A", "kicker": "K"}
    after = {"title": "B", "sub": "S"}
    change = versioning.diff("meta", before, after)
    assert change["added"] == {"sub": "S"}
    assert change["removed"] == {"kicker": "K"}
    assert change["changed"] == {"title": ["A", "B"]}

    text = versioning.phrase("meta", change)
    assert "Added sub" in text
    assert "Removed kicker" in text
    assert "Changed title" in text


def test_diff_and_phrase_list_resource_add_remove_change():
    before = [{"n": "Day 1", "title": "X"}, {"n": "Day 2", "title": "Y"}]
    after = [{"n": "Day 1", "title": "X2"}, {"n": "Day 3", "title": "Z"}]
    change = versioning.diff("days", before, after)

    assert [i["n"] for i in change["added"]] == ["Day 3"]
    assert [i["n"] for i in change["removed"]] == ["Day 2"]
    assert change["changed"][0]["id"] == "Day 1"
    assert change["reordered"] is False

    text = versioning.phrase("days", change)
    assert "Added Day 3" in text
    assert "Removed Day 2" in text
    assert "Changed Day 1" in text


def test_diff_detects_pure_reorder():
    before = [{"n": "Day 1"}, {"n": "Day 2"}]
    after = [{"n": "Day 2"}, {"n": "Day 1"}]
    change = versioning.diff("days", before, after)
    assert change["added"] == [] and change["removed"] == [] and change["changed"] == []
    assert change["reordered"] is True
    assert versioning.phrase("days", change) == "Reordered"


def test_delete_checklist_item_then_restore_from_trash():
    with edit_context.editing(actor="Dad"):
        item = trip_service.add_checklist_item("Bring tent")
    with edit_context.editing(actor="Dad", message="not needed after all"):
        trip_service.remove_checklist_item(item["id"])

    trash = versioning.find_deleted_items("checklist")
    assert len(trash) == 1
    assert trash[0]["id"] == item["id"]
    assert trash[0]["deletedBy"] == "Dad"
    assert trash[0]["content"] == item

    with edit_context.editing(actor="Mum", message="actually we do need it"):
        restored = trip_service.restore_checklist_item(trash[0]["content"])

    assert restored == item
    assert trip_service.get_checklist() == [item]
    assert versioning.find_deleted_items("checklist") == []


def test_delete_day_then_restore_via_add_day():
    day = {"n": "Day 9", "title": "Extra day", "tl": []}
    with edit_context.editing(actor="Dad"):
        trip_service.add_day(day)
    with edit_context.editing(actor="Dad", message="cutting it for time"):
        trip_service.delete_day("Day 9")

    trash = versioning.find_deleted_items("days")
    assert len(trash) == 1
    assert trash[0]["id"] == "Day 9"

    with edit_context.editing(actor="Mum", message="putting it back"):
        trip_service.add_day(trash[0]["content"], op="restore_item")

    assert trip_service.get_day("Day 9")["title"] == "Extra day"
    assert versioning.find_deleted_items("days") == []
    entry = versioning.list_history("days")[0]
    assert entry["op"] == "restore_item"


def test_restoring_expense_with_reused_id_raises_validation_error():
    entry = {"date": "2026-01-01", "amount": 500, "paidBy": "Dad", "currency": "INR"}
    with edit_context.editing(actor="Dad"):
        added = trip_service.add_expense(entry)
    with pytest.raises(ValidationError):
        trip_service.add_expense(dict(added), op="restore_item")


def test_ensure_baselines_seeds_once_and_never_clobbers():
    storage.save_json("meta.json", {"title": "Pre-existing"})
    versioning.ensure_baselines()

    history = versioning.list_history("meta")
    assert len(history) == 1
    assert history[0]["op"] == "baseline"
    assert versioning.get_snapshot("meta", 1) == {"title": "Pre-existing"}

    with edit_context.editing(actor="Mum"):
        trip_service.update_meta({"title": "Changed"})
    versioning.ensure_baselines()  # must be a no-op now

    history = versioning.list_history("meta")
    assert len(history) == 2


def test_restore_version_preserves_full_history():
    with edit_context.editing(actor="Mum"):
        trip_service.update_meta({"title": "V1"})
    with edit_context.editing(actor="Dad"):
        trip_service.update_meta({"title": "V2"})

    v1_snapshot = versioning.get_snapshot("meta", 1)
    with edit_context.editing(actor="Mum", message="revert to V1"):
        trip_service.restore_resource("meta", v1_snapshot)

    history = versioning.list_history("meta")  # newest first
    assert len(history) == 3
    assert history[0]["op"] == "restore"
    assert history[0]["version"] == 3
    assert trip_service.get_meta()["title"] == "V1"


def test_feed_merges_and_sorts_across_resources_newest_first():
    with edit_context.editing(actor="Mum"):
        trip_service.update_meta({"title": "T"})
    with edit_context.editing(actor="Dad"):
        trip_service.update_budget({"vehicle": []})

    rows = versioning.feed()
    assert len(rows) == 2
    assert rows[0]["ts"] >= rows[1]["ts"]
    resources = {r["resource"] for r in rows}
    assert resources == {"meta", "budget"}


def test_entry_diff_matches_history_transition():
    with edit_context.editing(actor="Mum"):
        trip_service.update_meta({"title": "First"})
    with edit_context.editing(actor="Dad"):
        trip_service.update_meta({"title": "Second"})

    change = versioning.entry_diff("meta", 2)
    assert change["changed"]["title"] == ["First", "Second"]
