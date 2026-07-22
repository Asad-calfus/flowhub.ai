from datetime import datetime

from app.models.analysis import AnalysisResult
from app.models.feedback import Feedback


def _seed_feedback(db_session, fid, day, module="Dashboard", sentiment="Negative", tier="Pro"):
    fb = Feedback(
        id=fid, feedback_text=f"Feedback {fid} about {module}.",
        feedback_created_at=datetime(2026, 5, day, 10, 0),
        customer_tier=tier, processing_status="processed",
    )
    an = AnalysisResult(
        feedback_id=fid, feedback_type="Bug report", category="Technical Issue", product_module=module,
        sentiment=sentiment, urgency="Medium", confidence=0.8, reasoning="x", model_name="baseline-rule-vader",
    )
    db_session.add_all([fb, an])


def test_generate_deterministic_report_via_api(client, db_session):
    _seed_feedback(db_session, "FB-R01", 2)
    _seed_feedback(db_session, "FB-R02", 3)
    db_session.commit()

    resp = client.post(
        "/api/v1/reports/weekly",
        json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["generation_method"] == "deterministic"
    assert body["report"]["summary_metrics"]["total_feedback"] == 2
    assert "executive_summary" in body["report"]
    assert body["markdown"].startswith("# Weekly Customer Feedback Report")


def test_generate_report_with_module_and_tier_filters(client, db_session):
    _seed_feedback(db_session, "FB-RF1", 2, module="Dashboard", tier="Enterprise")
    _seed_feedback(db_session, "FB-RF2", 2, module="Billing", tier="Pro")
    db_session.commit()

    resp = client.post(
        "/api/v1/reports/weekly",
        json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic", "product_module": "Dashboard"},
    )
    assert resp.status_code == 201
    assert resp.json()["report"]["summary_metrics"]["total_feedback"] == 1
    assert resp.json()["product_module_filter"] == "Dashboard"


def test_empty_period_report_via_api_does_not_error(client, db_session):
    resp = client.post(
        "/api/v1/reports/weekly",
        json={"start_date": "2026-01-01", "end_date": "2026-01-07", "mode": "deterministic"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["report"]["summary_metrics"]["total_feedback"] == 0
    assert body["report"]["top_pain_points"] == []


def test_generate_all_time_report_via_api_omits_dates(client, db_session):
    _seed_feedback(db_session, "FB-AT01", 2)
    db_session.add(Feedback(id="FB-AT02", feedback_text="dateless import", feedback_created_at=None, customer_tier="Pro", processing_status="processed"))
    db_session.commit()

    resp = client.post("/api/v1/reports/weekly", json={"mode": "deterministic"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_all_time"] is True
    assert body["report"]["period"]["is_all_time"] is True
    assert body["report"]["summary_metrics"]["total_feedback"] == 2


def test_report_rejects_only_one_date_given(client):
    resp = client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "mode": "deterministic"})
    assert resp.status_code == 422


def test_live_llm_report_without_api_key_returns_503(client, db_session):
    _seed_feedback(db_session, "FB-R03", 2)
    db_session.commit()
    resp = client.post(
        "/api/v1/reports/weekly",
        json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "live"},
    )
    assert resp.status_code == 503


def test_dry_run_llm_report_via_api(client, db_session):
    _seed_feedback(db_session, "FB-R04", 2)
    db_session.commit()
    resp = client.post(
        "/api/v1/reports/weekly",
        json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "dry_run"},
    )
    assert resp.status_code == 201
    assert resp.json()["generation_method"] == "dry_run"


def test_report_persistence_and_retrieval(client, db_session):
    _seed_feedback(db_session, "FB-R05", 2)
    db_session.commit()
    create_resp = client.post(
        "/api/v1/reports/weekly",
        json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"},
    )
    report_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/reports/{report_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == report_id
    assert get_resp.json()["report"]["summary_metrics"]["total_feedback"] == 1


def test_download_report_pdf(client, db_session):
    _seed_feedback(db_session, "FB-PDF1", 2)
    db_session.commit()
    create_resp = client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"})
    report_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/reports/{report_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_download_missing_report_pdf_returns_404(client):
    resp = client.get("/api/v1/reports/RPT-9999/pdf")
    assert resp.status_code == 404


def test_share_link_token_grants_pdf_access(client, db_session):
    _seed_feedback(db_session, "FB-PDF2", 2)
    db_session.commit()
    create_resp = client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"})
    report_id = create_resp.json()["id"]

    share_resp = client.post(f"/api/v1/reports/{report_id}/share")
    assert share_resp.status_code == 200
    body = share_resp.json()
    assert body["report_id"] == report_id
    assert "token=" in body["path"]

    resp = client.get(f"/api/v1/reports/{report_id}/pdf", params={"token": body["token"]})
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


def test_pdf_rejects_invalid_token(client, db_session):
    _seed_feedback(db_session, "FB-PDF3", 2)
    db_session.commit()
    create_resp = client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"})
    report_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/reports/{report_id}/pdf", params={"token": "not-a-real-token"})
    assert resp.status_code == 403


def test_pdf_rejects_token_for_a_different_report(client, db_session):
    _seed_feedback(db_session, "FB-PDF4", 2)
    _seed_feedback(db_session, "FB-PDF5", 3)
    db_session.commit()
    report_a = client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"}).json()["id"]
    report_b = client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic", "product_module": "Billing"}).json()["id"]

    token = client.post(f"/api/v1/reports/{report_a}/share").json()["token"]
    resp = client.get(f"/api/v1/reports/{report_b}/pdf", params={"token": token})
    assert resp.status_code == 403


def test_get_missing_report_returns_404(client):
    resp = client.get("/api/v1/reports/RPT-9999")
    assert resp.status_code == 404


def test_list_reports(client, db_session):
    _seed_feedback(db_session, "FB-R06", 2)
    db_session.commit()
    client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-01", "end_date": "2026-05-07", "mode": "deterministic"})
    client.post("/api/v1/reports/weekly", json={"start_date": "2026-05-08", "end_date": "2026-05-14", "mode": "deterministic"})

    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
