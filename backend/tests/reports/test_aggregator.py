from datetime import date, datetime

from app.models.analysis import AnalysisResult
from app.models.context import ContextMatch, ContextRecord
from app.models.feedback import Feedback
from app.models.theme import Theme, ThemeMember
from src.reports.aggregator import aggregate_period, previous_period


def _feedback(fid, day, module, sentiment, tier="Pro", urgency="Medium", confidence=0.8, source="Support ticket", month=5):
    return (
        Feedback(
            id=fid,
            feedback_text=f"Feedback {fid}",
            source=source,
            feedback_created_at=datetime(2026, month, day, 10, 0),
            customer_tier=tier,
            processing_status="processed",
        ),
        AnalysisResult(
            feedback_id=fid,
            feedback_type="Bug report",
            category="Technical Issue",
            product_module=module,
            sentiment=sentiment,
            urgency=urgency,
            confidence=confidence,
            reasoning="x",
            model_name="baseline-rule-vader",
        ),
    )


def test_date_range_filtering_excludes_outside_period(db_session):
    fb1, an1 = _feedback("FB-D01", 5, "Dashboard", "Negative")
    fb2, an2 = _feedback("FB-D02", 20, "Dashboard", "Negative")  # outside range
    db_session.add_all([fb1, fb2, an1, an2])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert agg.metrics.total_feedback == 1
    assert "FB-D01" in agg.feedback_by_id
    assert "FB-D02" not in agg.feedback_by_id


def test_aggregation_correctness_counts_and_distributions(db_session):
    rows = [
        _feedback("FB-A01", 2, "Dashboard", "Negative"),
        _feedback("FB-A02", 3, "Dashboard", "Negative"),
        _feedback("FB-A03", 3, "Billing", "Positive"),
        _feedback("FB-A04", 4, "Billing", "Neutral", tier="Enterprise"),
    ]
    for fb, an in rows:
        db_session.add_all([fb, an])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert agg.metrics.total_feedback == 4
    assert agg.metrics.feedback_by_product_module == {"Dashboard": 2, "Billing": 2}
    assert agg.metrics.feedback_by_customer_tier == {"Pro": 3, "Enterprise": 1}
    assert agg.metrics.sentiment_distribution["Negative"] == 0.5


def test_module_negative_ratio_percentage(db_session):
    rows = [
        _feedback("FB-M01", 2, "Dashboard", "Negative"),
        _feedback("FB-M02", 2, "Dashboard", "Negative"),
        _feedback("FB-M03", 2, "Dashboard", "Positive"),
    ]
    for fb, an in rows:
        db_session.add_all([fb, an])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    dashboard = next(m for m in agg.modules if m.entity_id == "Dashboard")
    assert dashboard.current_count == 3
    assert dashboard.extra["negative_ratio"] == round(2 / 3, 4)


def test_week_over_week_theme_trend_growing(db_session):
    # previous week (2026-04-24..04-30): 2 members; current week: 5 members -> >20% growth
    theme = Theme(id="THM-X", name="Slow dashboard", keywords=["slow"], feedback_count=7)
    db_session.add(theme)
    members = []
    for i, day in enumerate([25, 26]):
        fb, an = _feedback(f"FB-P0{i}", day, "Dashboard", "Negative", month=4)
        db_session.add_all([fb, an])
        members.append(ThemeMember(theme_id="THM-X", feedback_id=fb.id))
    for i, day in enumerate([1, 2, 3, 4, 5]):
        fb, an = _feedback(f"FB-C0{i}", day, "Dashboard", "Negative")
        db_session.add_all([fb, an])
        members.append(ThemeMember(theme_id="THM-X", feedback_id=fb.id))
    db_session.add_all(members)
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    stat = next(t for t in agg.themes if t.entity_id == "THM-X")
    assert stat.current_count == 5
    assert stat.previous_count == 2
    assert stat.trend == "growing"
    assert stat.percent_change == 150.0


def test_theme_trend_new_when_no_previous_period_members(db_session):
    theme = Theme(id="THM-NEW", name="New theme", keywords=[], feedback_count=2)
    db_session.add(theme)
    fb1, an1 = _feedback("FB-N01", 2, "Billing", "Negative")
    fb2, an2 = _feedback("FB-N02", 3, "Billing", "Negative")
    db_session.add_all([fb1, an1, fb2, an2, ThemeMember(theme_id="THM-NEW", feedback_id="FB-N01"), ThemeMember(theme_id="THM-NEW", feedback_id="FB-N02")])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    stat = next(t for t in agg.themes if t.entity_id == "THM-NEW")
    assert stat.trend == "new"
    assert stat.percent_change is None


def test_known_bug_matched_counts_and_trend(db_session):
    bug = ContextRecord(id="BUG-001", context_type="known_bug", title="SSO logout bug", status="Open", product_module="Authentication")
    db_session.add(bug)
    for i, day in enumerate([2, 3, 4]):
        fb, an = _feedback(f"FB-B0{i}", day, "Authentication", "Negative")
        db_session.add_all([fb, an])
        db_session.add(ContextMatch(feedback_id=fb.id, context_record_id="BUG-001", match_type="known_bug", similarity_score=0.9, rank=1, match_status="matched"))
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert len(agg.known_bugs) == 1
    assert agg.known_bugs[0].current_count == 3
    assert agg.known_bugs[0].title == "SSO logout bug"


def test_new_untracked_issue_detection(db_session):
    fb, an = _feedback("FB-U01", 2, "Reports", "Negative")
    db_session.add_all([fb, an])
    db_session.add(ContextMatch(feedback_id="FB-U01", context_record_id="BUG-999", match_type="known_bug", similarity_score=0.1, rank=1, match_status="candidate"))
    db_session.add(ContextRecord(id="BUG-999", context_type="known_bug", title="Unrelated", status="Open"))
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert agg.metrics.new_issue_count == 1
    all_new_ids = {fid for c in agg.new_issue_clusters for fid in c.feedback_ids}
    assert "FB-U01" in all_new_ids


def test_unprocessed_feedback_not_counted_as_new_issue(db_session):
    fb, an = _feedback("FB-UP01", 2, "Reports", "Negative")
    db_session.add_all([fb, an])
    db_session.commit()  # no context_matches rows at all

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert agg.metrics.new_issue_count == 0
    assert any("not been run through context-match retrieval" in note for note in agg.data_limitations)


def test_enterprise_negative_feedback_detected(db_session):
    fb, an = _feedback("FB-E01", 2, "Billing", "Negative", tier="Enterprise")
    db_session.add_all([fb, an])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert agg.enterprise_negative_feedback_ids == ["FB-E01"]


def test_customer_tier_and_product_module_filters(db_session):
    fb1, an1 = _feedback("FB-F01", 2, "Dashboard", "Negative", tier="Enterprise")
    fb2, an2 = _feedback("FB-F02", 2, "Billing", "Negative", tier="Pro")
    db_session.add_all([fb1, an1, fb2, an2])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7), product_module="Dashboard")
    assert agg.metrics.total_feedback == 1
    assert "FB-F01" in agg.feedback_by_id

    agg2 = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7), customer_tier="Pro")
    assert agg2.metrics.total_feedback == 1
    assert "FB-F02" in agg2.feedback_by_id


def test_empty_period_returns_zero_metrics_without_error(db_session):
    agg = aggregate_period(db_session, date(2026, 6, 1), date(2026, 6, 7))
    assert agg.metrics.total_feedback == 0
    assert agg.metrics.sentiment_distribution == {}
    assert agg.themes == []
    assert agg.known_bugs == []
    assert agg.data_limitations == []


def test_previous_period_helper_matches_current_period_length():
    prev_start, prev_end = previous_period(date(2026, 5, 8), date(2026, 5, 14))
    assert prev_start == date(2026, 5, 1)
    assert prev_end == date(2026, 5, 7)


def test_recommended_action_triggered_for_repeated_known_bug(db_session):
    bug = ContextRecord(id="BUG-002", context_type="known_bug", title="Notif delay", status="Open")
    db_session.add(bug)
    for i, day in enumerate([2, 3, 4]):
        fb, an = _feedback(f"FB-RA0{i}", day, "Notifications", "Negative")
        db_session.add_all([fb, an])
        db_session.add(ContextMatch(feedback_id=fb.id, context_record_id="BUG-002", match_type="known_bug", similarity_score=0.9, rank=1, match_status="matched"))
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    action_types = {a["action_type"] for a in agg.recommended_actions}
    assert "review_bug_priority" in action_types


def test_all_time_mode_includes_every_record_regardless_of_date(db_session):
    rows = [
        _feedback("FB-AT01", 2, "Dashboard", "Negative", month=1),
        _feedback("FB-AT02", 3, "Billing", "Positive", month=7),
    ]
    for fb, an in rows:
        db_session.add_all([fb, an])
    # a record with no feedback_created_at at all must still be included
    db_session.add(Feedback(id="FB-AT03", feedback_text="no date", source="CSV", feedback_created_at=None, customer_tier="Pro", processing_status="processed"))
    db_session.commit()

    agg = aggregate_period(db_session, None, None)
    assert agg.all_time is True
    assert agg.metrics.total_feedback == 3
    assert {"FB-AT01", "FB-AT02", "FB-AT03"} <= set(agg.feedback_by_id)
    assert agg.prev_start_date is None
    assert agg.prev_end_date is None


def test_all_time_mode_reports_all_time_trend_not_new(db_session):
    theme = Theme(id="THM-AT", name="All time theme", keywords=[], feedback_count=2)
    db_session.add(theme)
    fb1, an1 = _feedback("FB-ATT01", 2, "Billing", "Negative")
    fb2, an2 = _feedback("FB-ATT02", 3, "Billing", "Negative")
    db_session.add_all(
        [fb1, an1, fb2, an2, ThemeMember(theme_id="THM-AT", feedback_id="FB-ATT01"), ThemeMember(theme_id="THM-AT", feedback_id="FB-ATT02")]
    )
    db_session.commit()

    agg = aggregate_period(db_session, None, None)
    stat = next(t for t in agg.themes if t.entity_id == "THM-AT")
    assert stat.trend == "all_time"
    assert stat.percent_change is None


def test_all_time_mode_rejects_only_one_date_given():
    import pytest

    with pytest.raises(ValueError):
        aggregate_period(None, date(2026, 5, 1), None)


def test_low_confidence_cluster_triggers_human_review_action(db_session):
    for i, day in enumerate([2, 3, 4]):
        fb, an = _feedback(f"FB-LC0{i}", day, "Reports", "Neutral", confidence=0.2)
        db_session.add_all([fb, an])
    db_session.commit()

    agg = aggregate_period(db_session, date(2026, 5, 1), date(2026, 5, 7))
    assert agg.metrics.low_confidence_count == 3
    action_types = {a["action_type"] for a in agg.recommended_actions}
    assert "human_review" in action_types
