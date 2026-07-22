"""Shapes a `PeriodAggregate` (src.reports.aggregator) into a compact, size-bounded
`EvidencePack` - the only representation of the period ever handed to an LLM prompt or
used to render the deterministic baseline. Raw feedback beyond the sampled
representatives never leaves this module.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.context import ContextRecord
from src.reports.aggregator import EntityStat, PeriodAggregate
from src.reports.schemas import (
    MAX_CONTEXT_PER_SECTION,
    MAX_REPRESENTATIVES,
    MAX_THEMES,
    EvidenceContext,
    EvidenceEnterprise,
    EvidenceModule,
    EvidenceNewIssueCluster,
    EvidencePack,
    EvidenceRecommendedAction,
    EvidenceTheme,
    RepresentativeFeedback,
    ReportingPeriod,
)

_URGENCY_RANK = {"High": 0, "Medium": 1, "Low": 2}


def _pick_representatives(aggregate: PeriodAggregate, feedback_ids: list[str], limit: int = MAX_REPRESENTATIVES) -> list[RepresentativeFeedback]:
    rows = [aggregate.feedback_by_id[fid] for fid in feedback_ids if fid in aggregate.feedback_by_id]
    rows.sort(key=lambda r: (_URGENCY_RANK.get(r.urgency, 1), r.feedback_id))
    return [
        RepresentativeFeedback(
            feedback_id=r.feedback_id,
            text_preview=r.feedback_text[:240],
            sentiment=r.sentiment,
            customer_tier=r.customer_tier,
        )
        for r in rows[:limit]
    ]


def _context_lookup(db: Session, entity_ids: list[str]) -> dict[str, ContextRecord]:
    if not entity_ids:
        return {}
    records = db.execute(select(ContextRecord).where(ContextRecord.id.in_(entity_ids))).scalars().all()
    return {r.id: r for r in records}


def _evidence_context(stat: EntityStat, context_type: str, record: ContextRecord | None, aggregate: PeriodAggregate) -> EvidenceContext:
    return EvidenceContext(
        context_id=stat.entity_id,
        context_type=context_type,
        title=stat.title,
        status=record.status if record else None,
        product_module=record.product_module if record else None,
        feedback_count=stat.current_count,
        percent_change=stat.percent_change,
        trend=stat.trend,
        representative_feedback=_pick_representatives(aggregate, stat.feedback_ids),
    )


def build_evidence_pack(db: Session, aggregate: PeriodAggregate) -> EvidencePack:
    period = ReportingPeriod(
        start_date=aggregate.start_date,
        end_date=aggregate.end_date,
        previous_period_start=aggregate.prev_start_date,
        previous_period_end=aggregate.prev_end_date,
        is_all_time=aggregate.all_time,
    )

    top_themes = aggregate.themes[:MAX_THEMES]
    evidence_themes = [
        EvidenceTheme(
            theme_id=t.entity_id,
            keywords=t.extra.get("keywords") or [],
            dominant_product_module=t.extra.get("dominant_product_module"),
            feedback_count=t.current_count,
            percent_change=t.percent_change,
            trend=t.trend,
            sentiment_distribution=t.extra.get("sentiment_distribution") or {},
            representative_feedback=_pick_representatives(aggregate, t.feedback_ids),
        )
        for t in top_themes
    ]

    evidence_modules = [
        EvidenceModule(
            product_module=m.entity_id,
            feedback_count=m.current_count,
            negative_ratio=m.extra["negative_ratio"],
            sentiment_distribution={},
            representative_feedback=_pick_representatives(
                aggregate, [fid for fid in m.feedback_ids if aggregate.feedback_by_id[fid].sentiment == "Negative"] or m.feedback_ids
            ),
        )
        for m in aggregate.modules
    ]

    context_ids = [s.entity_id for s in aggregate.known_bugs + aggregate.feature_requests + aggregate.releases]
    context_records = _context_lookup(db, context_ids)

    known_bugs = [
        _evidence_context(s, "known_bug", context_records.get(s.entity_id), aggregate)
        for s in aggregate.known_bugs[:MAX_CONTEXT_PER_SECTION]
    ]
    feature_requests = [
        _evidence_context(s, "feature_request", context_records.get(s.entity_id), aggregate)
        for s in aggregate.feature_requests[:MAX_CONTEXT_PER_SECTION]
    ]
    releases = [
        _evidence_context(s, "release", context_records.get(s.entity_id), aggregate)
        for s in aggregate.releases[:MAX_CONTEXT_PER_SECTION]
    ]

    new_issue_clusters = [
        EvidenceNewIssueCluster(
            cluster_id=c.entity_id,
            feedback_count=c.current_count,
            representative_feedback=_pick_representatives(aggregate, c.feedback_ids),
        )
        for c in aggregate.new_issue_clusters[:MAX_CONTEXT_PER_SECTION]
    ]

    enterprise = EvidenceEnterprise(
        negative_feedback_count=len(aggregate.enterprise_negative_feedback_ids),
        representative_feedback=_pick_representatives(aggregate, aggregate.enterprise_negative_feedback_ids),
    )

    recommended_actions = [
        EvidenceRecommendedAction(
            action_id=a["action_id"],
            action_type=a["action_type"],
            priority=a["priority"],
            related_theme_ids=a["related_theme_ids"],
            related_context_ids=a["related_context_ids"],
        )
        for a in aggregate.recommended_actions
    ]

    return EvidencePack(
        period=period,
        metrics=aggregate.metrics,
        top_themes=evidence_themes,
        modules=evidence_modules,
        known_bugs=known_bugs,
        feature_requests=feature_requests,
        releases=releases,
        new_issue_clusters=new_issue_clusters,
        enterprise=enterprise,
        recommended_actions=recommended_actions,
        data_limitations=list(aggregate.data_limitations),
    )
