"""Deterministic SQL + Python analytics over stored feedback/analysis/theme/context data.

Every number that ends up in a weekly report is computed here (or in
`evidence_builder`, which only samples/truncates what this module already computed) -
never by an LLM. `src.reports.generator` must never ask a model to invent, recompute, or
adjust any of these values.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.context import ContextMatch, ContextRecord
from app.models.feedback import Feedback
from app.models.theme import ThemeMember
from app.repositories import analysis as analysis_repo
from src.reports.schemas import SummaryMetrics
from src.retrieval.context_retriever import LOW_SIGNAL_THRESHOLD
from src.themes.trends import DECLINE_THRESHOLD_PCT, GROWTH_THRESHOLD_PCT

LOW_CONFIDENCE_THRESHOLD = 0.5
MIN_REPEAT_COUNT = 3  # min matched count in-period for a bug/feature/release to be "notable"
ENTERPRISE_ALERT_COUNT = 2
LOW_CONFIDENCE_CLUSTER_MIN = 3
MIN_MODULE_SAMPLE = 3  # ignore modules with fewer than this many feedback in-period


def _trend(current: int, previous: int) -> tuple[str, float | None]:
    """Same thresholds as src.themes.trends._trend_status, generalized to any entity
    with a current/previous period count rather than only themes."""
    if previous == 0:
        return ("new", None) if current > 0 else ("stable", None)
    pct = round((current - previous) / previous * 100, 2)
    if pct > GROWTH_THRESHOLD_PCT:
        return "growing", pct
    if pct < DECLINE_THRESHOLD_PCT:
        return "declining", pct
    return "stable", pct


def _distribution(values: list[str]) -> dict[str, float]:
    counts = Counter(v for v in values if v)
    total = sum(counts.values())
    return {k: round(v / total, 4) for k, v in counts.items()} if total else {}


def previous_period(start_date: date, end_date: date) -> tuple[date, date]:
    length = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    return prev_start, prev_end


def _all_time_bounds(db: Session, customer_tier: str | None, workspace_id: str) -> tuple[date, date]:
    """Display-only date range for an all-time report: the earliest/latest
    `feedback_created_at` in the workspace. Falls back to today for both ends if the
    workspace has no feedback yet, or none of it has a date (dateless imports)."""
    where_sql = ["workspace_id = :workspace_id"]
    params: dict = {"workspace_id": workspace_id}
    if customer_tier:
        where_sql.append("customer_tier = :customer_tier")
        params["customer_tier"] = customer_tier
    row = db.execute(
        text(f"SELECT MIN(feedback_created_at) AS lo, MAX(feedback_created_at) AS hi FROM feedback WHERE {' AND '.join(where_sql)}"),
        params,
    ).one()
    today = date.today()
    lo = row.lo.date() if row.lo is not None else today
    hi = row.hi.date() if row.hi is not None else today
    return lo, hi


@dataclass
class FeedbackRow:
    feedback_id: str
    feedback_text: str
    source: str | None
    customer_tier: str | None
    feedback_type: str | None = None
    product_module: str | None = None
    sentiment: str | None = None
    urgency: str | None = None
    confidence: float | None = None


@dataclass
class EntityStat:
    entity_id: str
    title: str
    current_count: int
    previous_count: int
    trend: str
    percent_change: float | None
    feedback_ids: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class PeriodAggregate:
    start_date: date
    end_date: date
    prev_start_date: date | None
    prev_end_date: date | None
    all_time: bool
    product_module_filter: str | None
    customer_tier_filter: str | None

    metrics: SummaryMetrics
    feedback_by_id: dict[str, FeedbackRow]
    themes: list[EntityStat]
    modules: list[EntityStat]
    known_bugs: list[EntityStat]
    feature_requests: list[EntityStat]
    releases: list[EntityStat]
    new_issue_clusters: list[EntityStat]
    enterprise_negative_feedback_ids: list[str]
    low_confidence_feedback_ids: list[str]
    recommended_actions: list[dict]
    data_limitations: list[str]


def _feedback_rows(
    db: Session, start_date: date | None, end_date: date | None, customer_tier: str | None, workspace_id: str
) -> dict[str, FeedbackRow]:
    """`start_date`/`end_date` both `None` means all-time: every record in the workspace
    is included regardless of `feedback_created_at`, including records with no date at all."""
    stmt = select(Feedback).where(Feedback.workspace_id == workspace_id)
    if start_date is not None and end_date is not None:
        stmt = stmt.where(
            Feedback.feedback_created_at >= start_date,
            Feedback.feedback_created_at < end_date + timedelta(days=1),
        )
    if customer_tier:
        stmt = stmt.where(Feedback.customer_tier == customer_tier)
    rows = db.execute(stmt).scalars().all()
    by_id = {
        r.id: FeedbackRow(feedback_id=r.id, feedback_text=r.feedback_text, source=r.source, customer_tier=r.customer_tier)
        for r in rows
    }
    analyses = analysis_repo.list_by_feedback_ids(db, list(by_id.keys()))
    for fid, analysis in analyses.items():
        row = by_id[fid]
        row.feedback_type = analysis.feedback_type
        row.product_module = analysis.product_module
        row.sentiment = analysis.sentiment
        row.urgency = analysis.urgency
        row.confidence = analysis.confidence
    return by_id


def _apply_module_filter(by_id: dict[str, FeedbackRow], product_module: str | None) -> dict[str, FeedbackRow]:
    if not product_module:
        return by_id
    return {fid: row for fid, row in by_id.items() if row.product_module == product_module}


# Dashboard-critical distributions/aggregates: raw SQL wrapped in text(), not ORM-loaded-then-
# Counter()'d in Python, per the standing SQLAlchemy-for-CRUD/text()-for-aggregations convention
# (GROUP BY, window functions, and aggregate functions belong here, not in application code).
_LATEST_ANALYSIS_CTE = """
    WITH latest_analysis AS (
        SELECT DISTINCT ON (feedback_id) feedback_id, feedback_type, product_module, sentiment, confidence
        FROM analysis_results
        ORDER BY feedback_id, created_at DESC
    )
"""


def _summary_metrics_sql(
    db: Session,
    start_date: date | None,
    end_date: date | None,
    customer_tier: str | None,
    product_module: str | None,
    workspace_id: str,
) -> SummaryMetrics:
    where_sql = ["f.workspace_id = :workspace_id"]
    params: dict = {"workspace_id": workspace_id}
    if start_date is not None and end_date is not None:
        where_sql += ["f.feedback_created_at >= :start_date", "f.feedback_created_at < :end_date_exclusive"]
        params["start_date"] = start_date
        params["end_date_exclusive"] = end_date + timedelta(days=1)
    if customer_tier:
        where_sql.append("f.customer_tier = :customer_tier")
        params["customer_tier"] = customer_tier
    if product_module:
        where_sql.append("la.product_module = :product_module")
        params["product_module"] = product_module
    where_clause = " AND ".join(where_sql)

    def _grouped_counts(select_expr: str) -> dict[str, int]:
        sql = f"""
            {_LATEST_ANALYSIS_CTE}
            SELECT {select_expr} AS key, COUNT(*) AS n
            FROM feedback f
            LEFT JOIN latest_analysis la ON la.feedback_id = f.id
            WHERE {where_clause}
            GROUP BY {select_expr}
        """
        return {row.key: row.n for row in db.execute(text(sql), params).all() if row.key is not None}

    feedback_by_source = _grouped_counts("COALESCE(f.source, 'unknown')")
    feedback_by_type = _grouped_counts("la.feedback_type")
    feedback_by_product_module = _grouped_counts("la.product_module")
    feedback_by_customer_tier = _grouped_counts("COALESCE(f.customer_tier, 'unknown')")
    sentiment_counts = _grouped_counts("la.sentiment")
    sentiment_total = sum(sentiment_counts.values())
    sentiment_distribution = (
        {k: round(v / sentiment_total, 4) for k, v in sentiment_counts.items()} if sentiment_total else {}
    )

    totals_sql = f"""
        {_LATEST_ANALYSIS_CTE}
        SELECT
            COUNT(*) AS total_feedback,
            COUNT(*) FILTER (WHERE la.confidence IS NOT NULL AND la.confidence < :low_conf_threshold)
                AS low_confidence_count,
            AVG(la.confidence) AS average_confidence
        FROM feedback f
        LEFT JOIN latest_analysis la ON la.feedback_id = f.id
        WHERE {where_clause}
    """
    totals = db.execute(text(totals_sql), {**params, "low_conf_threshold": LOW_CONFIDENCE_THRESHOLD}).one()

    return SummaryMetrics(
        total_feedback=totals.total_feedback,
        feedback_by_source=feedback_by_source,
        feedback_by_type=feedback_by_type,
        sentiment_distribution=sentiment_distribution,
        feedback_by_product_module=feedback_by_product_module,
        feedback_by_customer_tier=feedback_by_customer_tier,
        low_confidence_count=totals.low_confidence_count,
        average_confidence=round(totals.average_confidence, 4) if totals.average_confidence is not None else None,
    )


def _theme_counts(db: Session, feedback_ids: set[str]) -> dict[str, list[str]]:
    if not feedback_ids:
        return {}
    stmt = select(ThemeMember.theme_id, ThemeMember.feedback_id).where(ThemeMember.feedback_id.in_(feedback_ids))
    result: dict[str, list[str]] = {}
    for theme_id, feedback_id in db.execute(stmt).all():
        result.setdefault(theme_id, []).append(feedback_id)
    return result


def _context_matched_counts(db: Session, feedback_ids: set[str], match_type: str) -> dict[str, list[str]]:
    if not feedback_ids:
        return {}
    stmt = select(ContextMatch.context_record_id, ContextMatch.feedback_id).where(
        ContextMatch.feedback_id.in_(feedback_ids),
        ContextMatch.match_type == match_type,
        ContextMatch.match_status == "matched",
    )
    result: dict[str, list[str]] = {}
    for context_id, feedback_id in db.execute(stmt).all():
        result.setdefault(context_id, []).append(feedback_id)
    return result


def _new_untracked_feedback_ids(db: Session, feedback_ids: set[str]) -> tuple[set[str], set[str]]:
    """Returns (new_untracked_ids, unprocessed_ids). A feedback record only counts as
    "new/untracked" if retrieval has actually run for it (it has context_match rows) and
    none of those rows reached "matched" status with a best score >= LOW_SIGNAL_THRESHOLD -
    i.e. its status under `get_context_matches` would be "new_untracked_issue". Records with
    no context_match rows at all haven't been retrieval-processed yet and are reported
    separately as a data limitation, never silently counted as "new issues"."""
    if not feedback_ids:
        return set(), set()
    stmt = select(ContextMatch.feedback_id, ContextMatch.match_status, ContextMatch.similarity_score).where(
        ContextMatch.feedback_id.in_(feedback_ids)
    )
    best_score: dict[str, float] = {}
    has_matched: set[str] = set()
    processed: set[str] = set()
    for feedback_id, match_status, score in db.execute(stmt).all():
        processed.add(feedback_id)
        if match_status == "matched":
            has_matched.add(feedback_id)
        best_score[feedback_id] = max(best_score.get(feedback_id, -1.0), score)

    new_untracked = {
        fid
        for fid in processed
        if fid not in has_matched and best_score.get(fid, -1.0) < LOW_SIGNAL_THRESHOLD
    }
    unprocessed = feedback_ids - processed
    return new_untracked, unprocessed


def _entity_stats(
    counts_current: dict[str, list[str]],
    counts_previous: dict[str, list[str]],
    titles: dict[str, str],
    all_time: bool = False,
) -> list[EntityStat]:
    """`all_time=True` means there is no previous period to compare against - every
    entity gets the "all_time" trend (not "new", which would misleadingly imply growth
    against a non-existent baseline) and no percent_change."""
    stats = []
    for entity_id, current_ids in counts_current.items():
        prev_ids = counts_previous.get(entity_id, [])
        trend, pct = ("all_time", None) if all_time else _trend(len(current_ids), len(prev_ids))
        stats.append(
            EntityStat(
                entity_id=entity_id,
                title=titles.get(entity_id, entity_id),
                current_count=len(current_ids),
                previous_count=len(prev_ids),
                trend=trend,
                percent_change=pct,
                feedback_ids=sorted(current_ids),
            )
        )
    stats.sort(key=lambda s: -s.current_count)
    return stats


def _derive_recommended_actions(
    known_bugs: list[EntityStat],
    feature_requests: list[EntityStat],
    releases: list[EntityStat],
    themes: list[EntityStat],
    new_issue_clusters: list[EntityStat],
    enterprise_ids: list[str],
    low_confidence_ids: list[str],
) -> list[dict]:
    """Rule-based only - see docs/changelog for the phase 6 entry for the full rule table.
    An LLM may reword these later; it may never choose the action_type or priority."""
    actions: list[dict] = []
    n = 0

    def _next_id() -> str:
        nonlocal n
        n += 1
        return f"ACT-{n:03d}"

    for bug in known_bugs:
        if bug.current_count >= MIN_REPEAT_COUNT and bug.trend in ("growing", "new", "all_time"):
            actions.append({
                "action_id": _next_id(),
                "action_type": "review_bug_priority",
                "priority": "High" if bug.current_count >= MIN_REPEAT_COUNT * 2 else "Medium",
                "related_context_ids": [bug.entity_id],
                "related_theme_ids": [],
                "feedback_ids": bug.feedback_ids,
                "label": bug.title,
            })

    for cluster in new_issue_clusters:
        if cluster.current_count >= MIN_REPEAT_COUNT:
            actions.append({
                "action_id": _next_id(),
                "action_type": "investigate_new_issue",
                "priority": "High" if cluster.current_count >= MIN_REPEAT_COUNT * 2 else "Medium",
                "related_context_ids": [],
                "related_theme_ids": [cluster.entity_id] if cluster.entity_id != "UNCLUSTERED" else [],
                "feedback_ids": cluster.feedback_ids,
                "label": cluster.title,
            })

    for fr in feature_requests:
        if fr.current_count >= MIN_REPEAT_COUNT:
            actions.append({
                "action_id": _next_id(),
                "action_type": "review_roadmap_priority",
                "priority": "Medium",
                "related_context_ids": [fr.entity_id],
                "related_theme_ids": [],
                "feedback_ids": fr.feedback_ids,
                "label": fr.title,
            })

    for rel in releases:
        if rel.current_count >= MIN_REPEAT_COUNT:
            actions.append({
                "action_id": _next_id(),
                "action_type": "inspect_release",
                "priority": "High" if rel.current_count >= MIN_REPEAT_COUNT * 2 else "Medium",
                "related_context_ids": [rel.entity_id],
                "related_theme_ids": [],
                "feedback_ids": rel.feedback_ids,
                "label": rel.title,
            })

    if len(enterprise_ids) >= ENTERPRISE_ALERT_COUNT:
        actions.append({
            "action_id": _next_id(),
            "action_type": "enterprise_follow_up",
            "priority": "High",
            "related_context_ids": [],
            "related_theme_ids": [],
            "feedback_ids": sorted(enterprise_ids),
            "label": "Enterprise-tier negative feedback",
        })

    if len(low_confidence_ids) >= LOW_CONFIDENCE_CLUSTER_MIN:
        actions.append({
            "action_id": _next_id(),
            "action_type": "human_review",
            "priority": "Low",
            "related_context_ids": [],
            "related_theme_ids": [],
            "feedback_ids": sorted(low_confidence_ids),
            "label": "Low-confidence classifications",
        })

    return actions


def aggregate_period(
    db: Session,
    start_date: date | None,
    end_date: date | None,
    product_module: str | None = None,
    customer_tier: str | None = None,
    workspace_id: str = "demo",
) -> PeriodAggregate:
    """`start_date`/`end_date` both `None` requests an all-time report: every feedback
    record in the workspace is aggregated (including records with no `feedback_created_at`
    at all), there is no previous-period comparison, and every trend is reported as
    "all_time" rather than a period-over-period label. Passing exactly one of the two is
    a caller error."""
    if (start_date is None) != (end_date is None):
        raise ValueError("start_date and end_date must both be provided, or both omitted for an all-time report")
    all_time = start_date is None

    if all_time:
        prev_start, prev_end = None, None
        current_by_id = _apply_module_filter(
            _feedback_rows(db, None, None, customer_tier, workspace_id), product_module
        )
        previous_by_id: dict = {}
        start_date, end_date = _all_time_bounds(db, customer_tier, workspace_id)
    else:
        if end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        prev_start, prev_end = previous_period(start_date, end_date)
        current_by_id = _apply_module_filter(
            _feedback_rows(db, start_date, end_date, customer_tier, workspace_id), product_module
        )
        previous_by_id = _apply_module_filter(
            _feedback_rows(db, prev_start, prev_end, customer_tier, workspace_id), product_module
        )

    current_ids = set(current_by_id)
    rows = list(current_by_id.values())

    metrics = _summary_metrics_sql(
        db, None if all_time else start_date, None if all_time else end_date, customer_tier, product_module, workspace_id
    )

    theme_current = _theme_counts(db, current_ids)
    theme_previous = _theme_counts(db, set(previous_by_id))
    theme_ids_needed = set(theme_current) | set(theme_previous)
    theme_records = {}
    if theme_ids_needed:
        from app.models.theme import Theme

        theme_records = {
            t.id: t for t in db.execute(select(Theme).where(Theme.id.in_(theme_ids_needed))).scalars().all()
        }
    theme_titles = {tid: (theme_records[tid].name if tid in theme_records else tid) for tid in theme_ids_needed}
    themes = _entity_stats(theme_current, theme_previous, theme_titles, all_time)
    row_by_id = {r.feedback_id: r for r in rows}
    for stat in themes:
        member_rows = [row_by_id[fid] for fid in stat.feedback_ids if fid in row_by_id]
        modules_in_theme = Counter(r.product_module for r in member_rows if r.product_module)
        stat.extra = {
            "keywords": theme_records[stat.entity_id].keywords if stat.entity_id in theme_records else [],
            "dominant_product_module": modules_in_theme.most_common(1)[0][0] if modules_in_theme else None,
            "sentiment_distribution": _distribution([r.sentiment for r in member_rows if r.sentiment]),
        }

    module_stats = []
    for module, count in metrics.feedback_by_product_module.items():
        if count < MIN_MODULE_SAMPLE:
            continue
        module_ids = [r.feedback_id for r in rows if r.product_module == module]
        neg = sum(1 for r in rows if r.product_module == module and r.sentiment == "Negative")
        module_stats.append(
            EntityStat(
                entity_id=module,
                title=module,
                current_count=count,
                previous_count=sum(1 for r in previous_by_id.values() if r.product_module == module),
                trend="all_time" if all_time else "stable",
                percent_change=None,
                feedback_ids=sorted(module_ids),
                extra={"negative_ratio": round(neg / count, 4), "negative_count": neg},
            )
        )
    module_stats.sort(key=lambda s: -s.extra["negative_ratio"])

    bugs_current = _context_matched_counts(db, current_ids, "known_bug")
    bugs_previous = _context_matched_counts(db, set(previous_by_id), "known_bug")
    frs_current = _context_matched_counts(db, current_ids, "feature_request")
    frs_previous = _context_matched_counts(db, set(previous_by_id), "feature_request")
    rels_current = _context_matched_counts(db, current_ids, "release")
    rels_previous = _context_matched_counts(db, set(previous_by_id), "release")

    all_context_ids = set(bugs_current) | set(bugs_previous) | set(frs_current) | set(frs_previous) | set(rels_current) | set(rels_previous)
    context_titles: dict[str, str] = {}
    if all_context_ids:
        records = db.execute(select(ContextRecord).where(ContextRecord.id.in_(all_context_ids))).scalars().all()
        context_titles = {r.id: r.title for r in records}

    known_bugs = _entity_stats(bugs_current, bugs_previous, context_titles, all_time)
    feature_requests = _entity_stats(frs_current, frs_previous, context_titles, all_time)
    releases = _entity_stats(rels_current, rels_previous, context_titles, all_time)

    new_untracked_ids, unprocessed_ids = _new_untracked_feedback_ids(db, current_ids)
    new_untracked_by_cluster: dict[str, list[str]] = {}
    theme_of_feedback = {fid: tid for tid, ids in theme_current.items() for fid in ids}
    for fid in new_untracked_ids:
        cluster_id = theme_of_feedback.get(fid, "UNCLUSTERED")
        new_untracked_by_cluster.setdefault(cluster_id, []).append(fid)
    new_issue_clusters = [
        EntityStat(
            entity_id=cluster_id,
            title=(theme_titles.get(cluster_id) or cluster_id),
            current_count=len(ids),
            previous_count=0,
            trend="new",
            percent_change=None,
            feedback_ids=sorted(ids),
        )
        for cluster_id, ids in new_untracked_by_cluster.items()
    ]
    new_issue_clusters.sort(key=lambda s: -s.current_count)
    metrics.new_issue_count = len(new_untracked_ids)

    enterprise_negative_ids = sorted(
        r.feedback_id for r in rows if r.customer_tier == "Enterprise" and r.sentiment == "Negative"
    )
    low_confidence_ids = sorted(
        r.feedback_id for r in rows if r.confidence is not None and r.confidence < LOW_CONFIDENCE_THRESHOLD
    )

    recommended_actions = _derive_recommended_actions(
        known_bugs, feature_requests, releases, themes, new_issue_clusters, enterprise_negative_ids, low_confidence_ids
    )

    data_limitations = []
    if unprocessed_ids:
        data_limitations.append(
            f"{len(unprocessed_ids)} feedback record(s) in this period have not been run through "
            "context-match retrieval yet, so they are excluded from known-bug/feature-request/"
            "new-issue counts (not counted as either matched or new)."
        )
    unanalyzed = [fid for fid, row in current_by_id.items() if row.sentiment is None]
    if unanalyzed:
        data_limitations.append(
            f"{len(unanalyzed)} feedback record(s) in this period have no stored classification "
            "result and are excluded from sentiment/type/module/confidence metrics."
        )
    if metrics.low_confidence_count:
        data_limitations.append(
            f"{metrics.low_confidence_count} classification(s) in this period have confidence below "
            f"{LOW_CONFIDENCE_THRESHOLD} and should be treated as lower-certainty evidence."
        )

    return PeriodAggregate(
        start_date=start_date,
        end_date=end_date,
        prev_start_date=prev_start,
        prev_end_date=prev_end,
        all_time=all_time,
        product_module_filter=product_module,
        customer_tier_filter=customer_tier,
        metrics=metrics,
        feedback_by_id=current_by_id,
        themes=themes,
        modules=module_stats,
        known_bugs=known_bugs,
        feature_requests=feature_requests,
        releases=releases,
        new_issue_clusters=new_issue_clusters,
        enterprise_negative_feedback_ids=enterprise_negative_ids,
        low_confidence_feedback_ids=low_confidence_ids,
        recommended_actions=recommended_actions,
        data_limitations=data_limitations,
    )
