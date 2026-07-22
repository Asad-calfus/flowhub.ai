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


def test_batch_retrieval_defaults_to_unprocessed_feedback(client):
    ids = [_create_feedback(client, f"Issue number {i} with the reports export.") for i in range(3)]
    resp = client.post("/api/v1/feedback/retrieval/batch", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["requested"] == 3
    assert body["succeeded"] == 3
    for feedback_id in ids:
        assert client.get(f"/api/v1/feedback/{feedback_id}/context-matches").json()["candidates"] == []


def test_batch_retrieval_skips_already_processed_feedback(client, db_session):
    from app.models.context import ContextMatch, ContextRecord

    processed_id = _create_feedback(client, "Already checked record about billing currency.")
    # A ContextMatch row is only ever created when retrieval finds at least one candidate
    # (see retrieval_service.get_context_matches) - insert one directly rather than relying
    # on seeded context records, to isolate what this test actually checks: that a record
    # with existing rows is skipped by the batch's "unprocessed" selection.
    db_session.add(ContextRecord(id="BUG-000", context_type="known_bug", title="Seed bug for this test"))
    db_session.add(
        ContextMatch(
            feedback_id=processed_id, context_record_id="BUG-000", match_type="known_bug",
            similarity_score=0.9, rank=1, match_status="matched",
        )
    )
    db_session.commit()
    pending_id = _create_feedback(client, "Still-pending record about notifications.")

    resp = client.post("/api/v1/feedback/retrieval/batch", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["requested"] == 1
    assert body["results"][0]["feedback_id"] == pending_id


def test_batch_retrieval_one_failure_does_not_roll_back_others(client):
    good_id = _create_feedback(client, "Billing charged me twice this month.")
    resp = client.post("/api/v1/feedback/retrieval/batch", json={"feedback_ids": [good_id, "FB-9999"]})
    body = resp.json()
    assert body["succeeded"] == 1
    assert body["failed"] == 1
    assert client.get(f"/api/v1/feedback/{good_id}/context-matches").status_code == 200
