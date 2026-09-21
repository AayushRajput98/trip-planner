"""End-to-end smoke test through the real FastAPI app: headers -> auth ->
edit_context -> trip_service -> versioning -> the /api/versions routes.
Mainly here to catch wiring bugs the unit-level tests can't (route ordering
for /feed and /trash vs. the /{resource} family, header names actually
matching what api.js sends, auth still being enforced on the new routes)."""
import os

os.environ["AUTH_TOKEN"] = "test-token"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token"}


def edit_headers(editor="Mum", message=None):
    headers = dict(AUTH, **{"X-Editor-Name": editor})
    if message:
        headers["X-Edit-Message"] = message
    return headers


def test_unauthenticated_write_is_rejected():
    res = client.put("/api/meta", json={"title": "Nope"})
    assert res.status_code == 401


def test_meta_update_appears_in_feed_with_actor_and_message():
    res = client.put(
        "/api/meta",
        json={"title": "Rajasthan Loop v2"},
        headers=edit_headers("Dad", "renamed the trip"),
    )
    assert res.status_code == 200

    feed = client.get("/api/versions/feed").json()
    assert feed, "expected at least one feed entry"
    top = feed[0]
    assert top["resource"] == "meta"
    assert top["actor"] == "Dad"
    assert top["message"] == "renamed the trip"
    assert "title" in top["summary"]


def test_delete_checklist_item_trash_and_restore_round_trip():
    added = client.post("/api/checklist", json={"text": "Sunscreen"}, headers=edit_headers()).json()

    client.delete(f"/api/checklist/{added['id']}", headers=edit_headers("Mum", "already have some"))

    trash = client.get("/api/versions/trash").json()
    assert any(row["resource"] == "checklist" and row["id"] == added["id"] for row in trash)

    restore = client.post(
        f"/api/versions/trash/checklist/{added['id']}/restore",
        headers=edit_headers("Dad", "we do need it"),
    )
    assert restore.status_code == 200
    assert restore.json()["id"] == added["id"]

    items = client.get("/api/checklist").json()
    assert any(i["id"] == added["id"] for i in items)

    trash_after = client.get("/api/versions/trash").json()
    assert not any(row["resource"] == "checklist" and row["id"] == added["id"] for row in trash_after)


def test_restore_whole_resource_version():
    client.put("/api/meta", json={"title": "First"}, headers=edit_headers())
    client.put("/api/meta", json={"title": "Second"}, headers=edit_headers())

    history = client.get("/api/versions/meta").json()  # newest first
    assert [h["version"] for h in history] == [2, 1]
    first_version = history[-1]["version"]

    restore = client.post(f"/api/versions/meta/{first_version}/restore", headers=edit_headers())
    assert restore.status_code == 200
    assert client.get("/api/meta").json()["title"] == "First"

    after = client.get("/api/versions/meta").json()
    assert [h["version"] for h in after] == [3, 2, 1]
    assert after[0]["op"] == "restore"


def test_restore_requires_auth():
    client.put("/api/meta", json={"title": "Something"}, headers=edit_headers())
    history = client.get("/api/versions/meta").json()
    version = history[-1]["version"]
    res = client.post(f"/api/versions/meta/{version}/restore")
    assert res.status_code == 401


def test_percent_encoded_message_header_round_trips():
    # api.js encodeURIComponent()s the note before sending it, since raw
    # non-ASCII (₹, accents, ...) isn't safe in an HTTP header value.
    import urllib.parse

    headers = edit_headers("Mum", None)
    headers["X-Edit-Message"] = urllib.parse.quote("fixed the ₹500 typo")

    client.put("/api/meta", json={"title": "Money talk"}, headers=headers)
    top = client.get("/api/versions/feed").json()[0]
    assert top["message"] == "fixed the ₹500 typo"


def test_unknown_resource_is_rejected():
    res = client.get("/api/versions/not-a-real-resource")
    assert res.status_code == 400
