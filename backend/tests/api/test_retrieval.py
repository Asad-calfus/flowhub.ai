def _create_feedback(client, text):
    return client.post("/api/v1/feedback", json={"feedback_text": text, "source": "Chat"}).json()["id"]


def test_similar_feedback_returns_other_record(client):
    id1 = _create_feedback(client, "SSO login fails a few seconds after signing in with Okta.")
    id2 = _create_feedback(client, "I cannot stay logged in with SSO, my session drops immediately.")
    resp = client.get(f"/api/v1/feedback/{id1}/similar")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["matched_feedback_id"] == id2
    assert body[0]["rank"] == 1


def test_similar_feedback_with_no_other_records_is_empty(client):
    id1 = _create_feedback(client, "The mobile app crashes when opening the reports tab.")
    resp = client.get(f"/api/v1/feedback/{id1}/similar")
    assert resp.status_code == 200
    assert resp.json() == []


def test_similar_feedback_missing_feedback_returns_404(client):
    resp = client.get("/api/v1/feedback/FB-9999/similar")
    assert resp.status_code == 404


def test_similar_feedback_top_k_is_bounded(client):
    id1 = _create_feedback(client, "Reports export is broken for CSV files.")
    resp = client.get(f"/api/v1/feedback/{id1}/similar", params={"top_k": 999})
    assert resp.status_code == 422


def test_context_matches_with_no_known_context_is_new_untracked_issue(client):
    feedback_id = _create_feedback(client, "The billing page shows the wrong currency for our account.")
    resp = client.get(f"/api/v1/feedback/{feedback_id}/context-matches")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "new_untracked_issue"
    assert body["matched_context_id"] is None
    assert body["candidates"] == []


def test_context_matches_missing_feedback_returns_404(client):
    resp = client.get("/api/v1/feedback/FB-9999/context-matches")
    assert resp.status_code == 404
