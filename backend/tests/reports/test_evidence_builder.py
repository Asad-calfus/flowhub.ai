from datetime import date, datetime

from app.models.analysis import AnalysisResult
from app.models.context import ContextMatch, ContextRecord
from app.models.feedback import Feedback
from app.models.theme import Theme, ThemeMember
from src.reports.aggregator import aggregate_period
from src.reports.evidence_builder import build_evidence_pack
from src.reports.schemas import MAX_CONTEXT_PER_SECTION, MAX_REPRESENTATIVES, MAX_THEMES


def _feedback(fid, day, module, sentiment):
    return (
        Feedback(id=fid, feedback_text=f"Text {fid}" * 20, feedback_created_at=datetime(2026, 5, day, 10, 0), processing_status="processed"),
        AnalysisResult(
            feedback_id=fid, feedback_type="Bug report", category="Technical Issue", product_module=module,
            sentiment=sentiment, urgency="High", confidence=0.9, reasoning="x", model_name="baseline-rule-vader",
        ),
    )


def test_evidence_pack_truncates_themes_to_max(db_session):
    for t in range(MAX_THEMES + 3):
        theme_id = f"THM-{t:03d}"
        db_session.add(Theme(id=theme_id, name=theme_id, keywords=[], feedback_count=5))
        for i in range(5):
            fid = f"FB-T{t}-{i}"
            fb, an = _feedback(fid, 2, "Dashboard", "Negative")
            db_session.add_all([fb, an, ThemeMember(theme_id=theme_id, feedback_id=fid)])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    pack = build_evidence_pack(db_session, agg)
    assert len(pack.top_themes) <= MAX_THEMES


def test_evidence_pack_truncates_representatives_per_theme(db_session):
    db_session.add(Theme(id="THM-BIG", name="Big theme", keywords=[], feedback_count=10))
    for i in range(10):
        fid = f"FB-BIG-{i}"
        fb, an = _feedback(fid, 2, "Dashboard", "Negative")
        db_session.add_all([fb, an, ThemeMember(theme_id="THM-BIG", feedback_id=fid)])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    pack = build_evidence_pack(db_session, agg)
    theme = next(t for t in pack.top_themes if t.theme_id == "THM-BIG")
    assert len(theme.representative_feedback) <= MAX_REPRESENTATIVES
    assert theme.feedback_count == 10  # count itself is NOT truncated, only the sample


def test_evidence_pack_truncates_context_sections_to_max(db_session):
    for b in range(MAX_CONTEXT_PER_SECTION + 2):
        bug_id = f"BUG-{b:03d}"
        db_session.add(ContextRecord(id=bug_id, context_type="known_bug", title=bug_id, status="Open"))
        fid = f"FB-BUG-{b}"
        fb, an = _feedback(fid, 2, "Authentication", "Negative")
        db_session.add_all([fb, an, ContextMatch(feedback_id=fid, context_record_id=bug_id, match_type="known_bug", similarity_score=0.9, rank=1, match_status="matched")])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    pack = build_evidence_pack(db_session, agg)
    assert len(pack.known_bugs) <= MAX_CONTEXT_PER_SECTION


def test_evidence_pack_carries_context_record_status_and_module(db_session):
    db_session.add(ContextRecord(id="BUG-S01", context_type="known_bug", title="Crash on save", status="In progress", product_module="Task Management"))
    fb, an = _feedback("FB-S01", 2, "Task Management", "Negative")
    db_session.add_all([fb, an, ContextMatch(feedback_id="FB-S01", context_record_id="BUG-S01", match_type="known_bug", similarity_score=0.9, rank=1, match_status="matched")])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    pack = build_evidence_pack(db_session, agg)
    bug = pack.known_bugs[0]
    assert bug.status == "In progress"
    assert bug.product_module == "Task Management"


def test_evidence_pack_no_raw_feedback_beyond_representatives(db_session):
    db_session.add(Theme(id="THM-RAW", name="raw", keywords=[], feedback_count=6))
    for i in range(6):
        fid = f"FB-RAW-{i}"
        fb, an = _feedback(fid, 2, "Dashboard", "Negative")
        db_session.add_all([fb, an, ThemeMember(theme_id="THM-RAW", feedback_id=fid)])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    pack = build_evidence_pack(db_session, agg)
    dumped = pack.model_dump()
    # every feedback_id appearing anywhere in the pack must be a sampled representative
    all_rep_ids = {r["feedback_id"] for t in dumped["top_themes"] for r in t["representative_feedback"]}
    assert len(all_rep_ids) <= MAX_REPRESENTATIVES
