"""Weekly per-theme trend statistics. Deterministic, rule-based - no anomaly detection.

Trend-status thresholds (documented, not tunable via env - simple enough to hardcode):
- "new": the theme's first week with any feedback (no prior week to compare against).
- "growing": percent_change > GROWTH_THRESHOLD_PCT (20%).
- "declining": percent_change < DECLINE_THRESHOLD_PCT (-20%).
- "stable": percent_change within [-20%, 20%].
"""

from collections import Counter
from datetime import datetime, timedelta

GROWTH_THRESHOLD_PCT = 20.0
DECLINE_THRESHOLD_PCT = -20.0


def _week_start(created_at: str) -> str:
    d = datetime.strptime(created_at[:10], "%Y-%m-%d")
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _distribution(rows: list[dict], field: str) -> dict[str, float]:
    counts = Counter(r.get(field) or "unknown" for r in rows)
    total = sum(counts.values())
    return {k: round(v / total, 4) for k, v in counts.items()} if total else {}


def _trend_status(prev_count: int | None, percent_change: float | None) -> str:
    if prev_count is None:
        return "new"
    if percent_change is None:
        return "stable"
    if percent_change > GROWTH_THRESHOLD_PCT:
        return "growing"
    if percent_change < DECLINE_THRESHOLD_PCT:
        return "declining"
    return "stable"


def compute_weekly_stats(theme_id: str, records: list[dict]) -> list[dict]:
    """records: full-column feedback rows (sentiment/customer_tier/product_module read
    here for reporting only, after clustering has already happened)."""
    weeks: dict[str, list[dict]] = {}
    for r in records:
        weeks.setdefault(_week_start(r["created_at"]), []).append(r)

    stats = []
    prev_count = None
    for week in sorted(weeks):
        rows = weeks[week]
        count = len(rows)
        change = count - prev_count if prev_count is not None else None
        pct = round((change / prev_count) * 100, 2) if prev_count is not None else None
        stats.append({
            "theme_id": theme_id,
            "week_start": week,
            "feedback_count": count,
            "change_from_previous_week": change,
            "percent_change": pct,
            "sentiment_distribution": _distribution(rows, "sentiment"),
            "customer_tier_distribution": _distribution(rows, "customer_tier"),
            "product_module_distribution": _distribution(rows, "product_module"),
            "trend_status": _trend_status(prev_count, pct),
        })
        prev_count = count
    return stats
