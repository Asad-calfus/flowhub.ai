def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_status_reports_database_connected(client):
    resp = client.get("/api/v1/status")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "connected"}
