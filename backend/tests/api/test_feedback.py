def _create(client, **overrides):
    payload = {"feedback_text": "The dashboard is very slow to load today.", "source": "Chat", "rating": 3}
    payload.update(overrides)
    return client.post("/api/v1/feedback", json=payload)


def test_create_feedback(client):
    resp = _create(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("FB-")
    assert body["feedback_text"] == "The dashboard is very slow to load today."
    assert body["processing_status"] == "pending"


def test_create_feedback_invalid_rating_rejected(client):
    resp = _create(client, rating=9)
    assert resp.status_code == 422


def test_get_feedback(client):
    created = _create(client).json()
    resp = client.get(f"/api/v1/feedback/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_missing_feedback_returns_404(client):
    resp = client.get("/api/v1/feedback/FB-9999")
    assert resp.status_code == 404


def test_delete_feedback(client):
    created = _create(client).json()
    resp = client.delete(f"/api/v1/feedback/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/v1/feedback/{created['id']}").status_code == 404


def test_delete_missing_feedback_returns_404(client):
    resp = client.delete("/api/v1/feedback/FB-9999")
    assert resp.status_code == 404


def test_list_feedback_pagination(client):
    for _ in range(3):
        _create(client)
    resp = client.get("/api/v1/feedback", params={"page": 1, "page_size": 2})
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1


def test_list_feedback_filter_by_source(client):
    _create(client, source="Chat")
    _create(client, source="Email")
    resp = client.get("/api/v1/feedback", params={"source": "Email"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["source"] == "Email"


def test_list_feedback_filter_by_customer_tier(client):
    _create(client, customer_tier="Enterprise")
    _create(client, customer_tier="Free")
    resp = client.get("/api/v1/feedback", params={"customer_tier": "Enterprise"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["customer_tier"] == "Enterprise"


def test_list_feedback_invalid_page_size_rejected(client):
    resp = client.get("/api/v1/feedback", params={"page_size": 0})
    assert resp.status_code == 422
