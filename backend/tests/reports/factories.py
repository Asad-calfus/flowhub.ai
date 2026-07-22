"""Hand-built EvidencePack fixtures for generator/evaluator tests that don't need a DB."""

from datetime import date

from src.reports.schemas import (
    EvidenceContext,
    EvidenceEnterprise,
    EvidenceModule,
    EvidenceNewIssueCluster,
    EvidencePack,
    EvidenceRecommendedAction,
    EvidenceTheme,
    RepresentativeFeedback,
    ReportingPeriod,
    SummaryMetrics,
)


def make_evidence_pack() -> EvidencePack:
    period = ReportingPeriod(
        start_date=date(2026, 5, 1), end_date=date(2026, 5, 7),
        previous_period_start=date(2026, 4, 24), previous_period_end=date(2026, 4, 30),
    )
    metrics = SummaryMetrics(
        total_feedback=10,
        feedback_by_source={"Support ticket": 6, "Survey": 4},
        feedback_by_type={"Bug report": 7, "Feature request": 3},
        sentiment_distribution={"Negative": 0.6, "Positive": 0.4},
        feedback_by_product_module={"Dashboard": 6, "Billing": 4},
        feedback_by_customer_tier={"Pro": 7, "Enterprise": 3},
        new_issue_count=1,
        low_confidence_count=1,
        average_confidence=0.75,
    )
    rep = [RepresentativeFeedback(feedback_id="FB-0001", text_preview="Dashboard is slow.", sentiment="Negative", customer_tier="Pro")]

    theme = EvidenceTheme(
        theme_id="THM-001", keywords=["dashboard", "slow"], dominant_product_module="Dashboard",
        feedback_count=6, percent_change=150.0, trend="growing",
        sentiment_distribution={"Negative": 1.0}, representative_feedback=rep,
    )
    module = EvidenceModule(
        product_module="Dashboard", feedback_count=6, negative_ratio=0.83,
        sentiment_distribution={"Negative": 0.83}, representative_feedback=rep,
    )
    bug = EvidenceContext(
        context_id="BUG-001", context_type="known_bug", title="SSO logout bug", status="Open",
        product_module="Authentication", feedback_count=4, percent_change=100.0, trend="growing",
        representative_feedback=rep,
    )
    feature = EvidenceContext(
        context_id="FR-001", context_type="feature_request", title="Dark mode", status="Planned",
        product_module="Dashboard", feedback_count=3, percent_change=None, trend="stable",
        representative_feedback=rep,
    )
    release = EvidenceContext(
        context_id="v2.4.0", context_type="release", title="v2.4.0", status=None,
        product_module=None, feedback_count=3, percent_change=None, trend="stable",
        representative_feedback=rep,
    )
    cluster = EvidenceNewIssueCluster(cluster_id="UNCLUSTERED", feedback_count=1, representative_feedback=rep)
    enterprise = EvidenceEnterprise(negative_feedback_count=2, representative_feedback=rep)
    action = EvidenceRecommendedAction(
        action_id="ACT-001", action_type="review_bug_priority", priority="High",
        related_theme_ids=[], related_context_ids=["BUG-001"],
    )

    return EvidencePack(
        period=period, metrics=metrics, top_themes=[theme], modules=[module],
        known_bugs=[bug], feature_requests=[feature], releases=[release],
        new_issue_clusters=[cluster], enterprise=enterprise, recommended_actions=[action],
        data_limitations=["1 feedback record has confidence below 0.5."],
    )
