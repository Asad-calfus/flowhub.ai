CSV_WITH_IDS = (
    "feedback_id,feedback_text,source,customer_tier,rating\n"
    "FB-TEST-01,App keeps crashing on startup,App review,Pro,2\n"
    "FB-TEST-02,Would love a dark mode option,Survey,Free,4\n"
)

CSV_MISSING_REQUIRED_COLUMN = "source,customer_tier\nChat,Pro\n"

CSV_WITH_ALIASED_COLUMNS = (
    "id,review_text,channel,tier,score\n"
    "EXT-01,App keeps crashing on startup,App review,Pro,2\n"
    "EXT-02,Would love a dark mode option,Survey,Free,4\n"
)

CSV_WITH_MESSY_VALUES = (
    "feedback_text,source,customer_tier,rating\n"
    "Login is broken after the update,Support Ticket,pro,not-a-number\n"
)


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


def test_import_csv_with_aliased_column_names(client):
    """Real-world CSVs won't use our exact header names - "review_text"/"channel"/"tier"/
    "score" should map to feedback_text/source/customer_tier/rating."""
    resp = _upload(client, CSV_WITH_ALIASED_COLUMNS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["feedback_imported"] == 2

    feedback = client.get("/api/v1/feedback/EXT-01").json()
    assert feedback["feedback_text"] == "App keeps crashing on startup"
    assert feedback["source"] == "App review"
    assert feedback["customer_tier"] == "Pro"
    assert feedback["rating"] == 2


def test_import_csv_with_messy_values_does_not_crash_batch_analysis(client):
    """Wrong-cased source/tier and an unparsable rating must still import, and must not
    crash live classification later - they degrade gracefully instead."""
    resp = _upload(client, CSV_WITH_MESSY_VALUES)
    assert resp.status_code == 200
    assert resp.json()["feedback_imported"] == 1

    batch = client.post("/api/v1/analysis/batch", json={"method": "baseline"})
    assert batch.status_code == 200
    assert batch.json()["succeeded"] == 1
