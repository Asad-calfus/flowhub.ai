from datetime import date

from app.models.analysis import AnalysisResult
from app.models.feedback import Feedback
from app.models.theme import Theme, ThemeMember


def _seed_theme(db_session):
    members = [
        Feedback(id="FB-T01", feedback_text="Dashboard widgets load slowly.", processing_status="processed"),
        Feedback(id="FB-T02", feedback_text="Dashboard takes forever to load today.", processing_status="processed"),
    ]
    db_session.add_all(members)
    db_session.add_all(
        [
            AnalysisResult(
                feedback_id="FB-T01", feedback_type="Performance issue", category="Technical Issue",
                product_module="Dashboard", sentiment="Negative", urgency="Medium", confidence=0.8,
                reasoning="slow", model_name="baseline-rule-vader",
            ),
            AnalysisResult(
                feedback_id="FB-T02", feedback_type="Performance issue", category="Technical Issue",
                product_module="Dashboard", sentiment="Negative", urgency="Medium", confidence=0.8,
                reasoning="slow", model_name="baseline-rule-vader",
            ),
        ]
    )
    db_session.add(
        Theme(
            id="THM-T01", name="Dashboard load slow", keywords=["dashboard", "slow"], feedback_count=2,
            first_seen=date(2026, 1, 1), last_seen=date(2026, 2, 1), trend_status="stable",
        )
    )
    db_session.add_all(
        [
            ThemeMember(theme_id="THM-T01", feedback_id="FB-T01", membership_score=1.0),
            ThemeMember(theme_id="THM-T01", feedback_id="FB-T02", membership_score=0.9),
        ]
    )
    db_session.commit()


def test_list_themes(client, db_session):
    _seed_theme(db_session)
    resp = client.get("/api/v1/themes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "THM-T01"


def test_get_theme_detail(client, db_session):
    _seed_theme(db_session)
    resp = client.get("/api/v1/themes/THM-T01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Dashboard load slow"
    assert body["sentiment_distribution"] == {"Negative": 1.0}
    assert len(body["representative_feedback"]) == 2
    assert len(body["members"]) == 2


def test_get_theme_detail_missing_returns_404(client):
    resp = client.get("/api/v1/themes/THM-9999")
    assert resp.status_code == 404


def test_get_theme_feedback(client, db_session):
    _seed_theme(db_session)
    resp = client.get("/api/v1/themes/THM-T01/feedback")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    ids = {item["id"] for item in body["items"]}
    assert ids == {"FB-T01", "FB-T02"}


def test_get_theme_feedback_missing_theme_returns_404(client):
    resp = client.get("/api/v1/themes/THM-9999/feedback")
    assert resp.status_code == 404
