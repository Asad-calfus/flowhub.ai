def _create_feedback_with_embedding(client, text):
    feedback_id = client.post("/api/v1/feedback", json={"feedback_text": text, "source": "Chat"}).json()["id"]
    client.get(f"/api/v1/feedback/{feedback_id}/similar")  # side effect: computes+stores the embedding
    return feedback_id


def test_ask_returns_dry_run_answer_with_sources(client):
    id1 = _create_feedback_with_embedding(client, "SSO login fails a few seconds after signing in with Okta.")
    _create_feedback_with_embedding(client, "Totally unrelated: the mobile app icon looks blurry.")

    resp = client.post("/api/v1/copilot/ask", json={"question": "Are customers having trouble logging in with SSO?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_name"] == "dry-run-stub"
    assert len(body["sources"]) >= 1
    assert any(s["feedback_id"] == id1 for s in body["sources"])


def test_ask_with_no_embedded_feedback_returns_no_related_message(client):
    resp = client.post("/api/v1/copilot/ask", json={"question": "Anything about billing?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"] == []
    assert "No related feedback" in body["answer"]


def test_ask_live_without_api_key_returns_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _create_feedback_with_embedding(client, "Reports export is broken for CSV files.")

    resp = client.post("/api/v1/copilot/ask", json={"question": "Are exports broken?", "live": True})
    assert resp.status_code == 503


def test_ask_rejects_empty_question(client):
    resp = client.post("/api/v1/copilot/ask", json={"question": ""})
    assert resp.status_code == 422


def test_ask_top_k_is_bounded(client):
    resp = client.post("/api/v1/copilot/ask", json={"question": "test", "top_k": 999})
    assert resp.status_code == 422
