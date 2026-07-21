CSV_WITH_IDS = (
    "feedback_id,feedback_text,source,customer_tier,rating\n"
    "FB-TEST-01,App keeps crashing on startup,App review,Pro,2\n"
    "FB-TEST-02,Would love a dark mode option,Survey,Free,4\n"
)

CSV_MISSING_REQUIRED_COLUMN = "source,customer_tier\nChat,Pro\n"


def _upload(client, content: str, filename: str = "feedback.csv"):
    return client.post(
        "/api/v1/feedback/import",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )


def test_import_csv_creates_feedback(client):
    resp = _upload(client, CSV_WITH_IDS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["feedback_imported"] == 2
    assert body["feedback_skipped"] == 0
    assert client.get("/api/v1/feedback/FB-TEST-01").status_code == 200


def test_import_csv_twice_prevents_duplicates(client):
    first = _upload(client, CSV_WITH_IDS).json()
    second = _upload(client, CSV_WITH_IDS).json()
    assert first["feedback_imported"] == 2
    assert second["feedback_imported"] == 0
    assert second["feedback_skipped"] == 2

    resp = client.get("/api/v1/feedback", params={"page_size": 100})
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids.count("FB-TEST-01") == 1


def test_import_invalid_csv_format_rejected(client):
    resp = _upload(client, CSV_MISSING_REQUIRED_COLUMN)
    assert resp.status_code == 400
