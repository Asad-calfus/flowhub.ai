def _create_feedback(client, text="Login keeps failing after the last update, very frustrating."):
    resp = client.post("/api/v1/feedback", json={"feedback_text": text, "source": "Support ticket"})
    return resp.json()["id"]


def test_baseline_analysis_is_stored(client):
    feedback_id = _create_feedback(client)
    resp = client.post(f"/api/v1/analysis/{feedback_id}", json={"method": "baseline"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["feedback_id"] == feedback_id
    assert body["model_name"] == "baseline-rule-vader"

    feedback = client.get(f"/api/v1/feedback/{feedback_id}").json()
    assert feedback["processing_status"] == "processed"


def test_get_analysis_returns_latest(client):
    feedback_id = _create_feedback(client)
    client.post(f"/api/v1/analysis/{feedback_id}", json={"method": "baseline"})
    resp = client.get(f"/api/v1/analysis/{feedback_id}")
    assert resp.status_code == 200
    assert resp.json()["feedback_id"] == feedback_id


def test_get_analysis_for_unanalyzed_feedback_returns_404(client):
    feedback_id = _create_feedback(client)
    resp = client.get(f"/api/v1/analysis/{feedback_id}")
    assert resp.status_code == 404


def test_analyze_missing_feedback_returns_404(client):
    resp = client.post("/api/v1/analysis/FB-9999", json={"method": "baseline"})
    assert resp.status_code == 404


def test_live_llm_without_api_key_returns_503(client):
    feedback_id = _create_feedback(client)
    resp = client.post(f"/api/v1/analysis/{feedback_id}", json={"method": "llm", "live": True})
    assert resp.status_code == 503


def test_batch_analysis_defaults_to_pending_feedback(client):
    ids = [_create_feedback(client, text=f"Issue number {i} with the reports export.") for i in range(3)]
    resp = client.post("/api/v1/analysis/batch", json={"method": "baseline"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["requested"] == 3
    assert body["succeeded"] == 3
    for feedback_id in ids:
        assert client.get(f"/api/v1/analysis/{feedback_id}").status_code == 200


def test_batch_analysis_one_failure_does_not_roll_back_others(client):
    good_id = _create_feedback(client, text="Billing charged me twice this month.")
    resp = client.post(
        "/api/v1/analysis/batch",
        json={"feedback_ids": [good_id, "FB-9999"], "method": "baseline"},
    )
    body = resp.json()
    assert body["succeeded"] == 1
    assert body["failed"] == 1
    assert client.get(f"/api/v1/analysis/{good_id}").status_code == 200
