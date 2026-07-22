"""Workspace isolation - an anonymous X-Workspace-Id header scopes feedback, themes, and
reports so a fresh workspace never sees another workspace's (or the demo's) data."""

from app.models.embedding import Embedding
from app.models.feedback import Feedback
from app.models.theme import Theme


def test_feedback_isolated_by_workspace(client):
    created = client.post(
        "/api/v1/feedback",
        json={"feedback_text": "Only visible in workspace A"},
        headers={"X-Workspace-Id": "ws-a"},
    )
    assert created.status_code == 201
    feedback_id = created.json()["id"]

    in_a = client.get("/api/v1/feedback", headers={"X-Workspace-Id": "ws-a"})
    assert any(item["id"] == feedback_id for item in in_a.json()["items"])

    in_b = client.get("/api/v1/feedback", headers={"X-Workspace-Id": "ws-b"})
    assert all(item["id"] != feedback_id for item in in_b.json()["items"])

    in_demo = client.get("/api/v1/feedback")  # no header -> defaults to "demo"
    assert all(item["id"] != feedback_id for item in in_demo.json()["items"])


def test_themes_isolated_by_workspace(client, db_session):
    db_session.add_all(
        [
            Theme(id="THM-A01", workspace_id="ws-a", name="Theme in A", keywords=[], feedback_count=1),
            Theme(id="THM-B01", workspace_id="ws-b", name="Theme in B", keywords=[], feedback_count=1),
        ]
    )
    db_session.commit()

    resp_a = client.get("/api/v1/themes", headers={"X-Workspace-Id": "ws-a"})
    ids_a = {item["id"] for item in resp_a.json()["items"]}
    assert ids_a == {"THM-A01"}

    resp_b = client.get("/api/v1/themes", headers={"X-Workspace-Id": "ws-b"})
    ids_b = {item["id"] for item in resp_b.json()["items"]}
    assert ids_b == {"THM-B01"}


def test_recompute_themes_scoped_to_calling_workspace(client, db_session):
    vector = [0.1] * 384
    for i in range(5):
        fid = f"FB-WS-{i}"
        db_session.add(Feedback(id=fid, workspace_id="ws-c", feedback_text=f"Near-duplicate complaint {i}"))
        db_session.add(Embedding(feedback_id=fid, vector=vector, embedding_model="test", text_hash=f"hash{i}"))
    db_session.commit()

    resp = client.post("/api/v1/themes/recompute", headers={"X-Workspace-Id": "ws-c"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["themes_created"] == 1
    assert body["feedback_assigned"] == 5
    assert body["feedback_unclustered"] == 0

    themes_c = client.get("/api/v1/themes", headers={"X-Workspace-Id": "ws-c"})
    assert themes_c.json()["total"] == 1

    themes_other = client.get("/api/v1/themes", headers={"X-Workspace-Id": "some-other-workspace"})
    assert themes_other.json()["total"] == 0


def test_recompute_themes_is_idempotent(client, db_session):
    vector = [0.2] * 384
    for i in range(4):
        fid = f"FB-WSI-{i}"
        db_session.add(Feedback(id=fid, workspace_id="ws-d", feedback_text=f"Repeated issue {i}"))
        db_session.add(Embedding(feedback_id=fid, vector=vector, embedding_model="test", text_hash=f"hashd{i}"))
    db_session.commit()

    headers = {"X-Workspace-Id": "ws-d"}
    first = client.post("/api/v1/themes/recompute", headers=headers).json()
    second = client.post("/api/v1/themes/recompute", headers=headers).json()
    assert first["themes_created"] == second["themes_created"] == 1

    total = client.get("/api/v1/themes", headers=headers).json()["total"]
    assert total == 1  # recompute replaces, not accumulates
