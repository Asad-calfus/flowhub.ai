from datetime import datetime

from app.models.analysis import AnalysisResult
from app.models.feedback import Feedback


def _seed(db_session, fid, customer_id, day, sentiment="Negative", urgency="Medium", tier="Enterprise"):
    fb = Feedback(
        id=fid, feedback_text=f"Feedback {fid}", customer_id=customer_id, customer_tier=tier,
        feedback_created_at=datetime(2026, 5, day, 10, 0), processing_status="processed",
    )
    an = AnalysisResult(
        feedback_id=fid, feedback_type="Bug report", category="Technical Issue", product_module="Billing",
        sentiment=sentiment, urgency=urgency, confidence=0.8, reasoning="x", model_name="baseline-rule-vader",
    )
    db_session.add_all([fb, an])


def test_at_risk_customer_ranked_high(client, db_session):
    _seed(db_session, "FB-C01", "CUST-1", 2, sentiment="Negative", urgency="High")
    _seed(db_session, "FB-C02", "CUST-1", 3, sentiment="Negative", urgency="High")
    _seed(db_session, "FB-C03", "CUST-2", 2, sentiment="Positive", urgency="Low")
    db_session.commit()

    resp = client.get("/api/v1/churn/customers")
    assert resp.status_code == 200
    body = resp.json()
    by_id = {c["customer_id"]: c for c in body}
    assert by_id["CUST-1"]["risk_level"] == "High"
    assert by_id["CUST-1"]["risk_score"] > by_id["CUST-2"]["risk_score"]
    assert body[0]["customer_id"] == "CUST-1"  # sorted descending by risk


def test_get_single_customer_risk(client, db_session):
    _seed(db_session, "FB-C10", "CUST-9", 2, sentiment="Negative", urgency="High")
    db_session.commit()

    resp = client.get("/api/v1/churn/customers/CUST-9")
    assert resp.status_code == 200
    assert resp.json()["customer_id"] == "CUST-9"
    assert resp.json()["total_feedback"] == 1


def test_unknown_customer_returns_404(client):
    resp = client.get("/api/v1/churn/customers/CUST-NOPE")
    assert resp.status_code == 404


def test_customer_with_no_negative_feedback_is_low_risk(client, db_session):
    _seed(db_session, "FB-C20", "CUST-HAPPY", 2, sentiment="Positive", urgency="Low")
    db_session.commit()

    resp = client.get("/api/v1/churn/customers/CUST-HAPPY")
    assert resp.json()["risk_level"] == "Low"
    assert resp.json()["risk_score"] == 0
