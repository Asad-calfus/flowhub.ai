from src.themes.trends import compute_weekly_stats


def _row(created_at, sentiment="Negative", tier="Pro", module="Dashboard"):
    return {"created_at": created_at, "sentiment": sentiment, "customer_tier": tier, "product_module": module}


def test_first_week_is_always_new():
    records = [_row("2026-05-04 10:00:00"), _row("2026-05-05 10:00:00")]
    stats = compute_weekly_stats("THM-001", records)
    assert stats[0]["trend_status"] == "new"
    assert stats[0]["change_from_previous_week"] is None


def test_growing_trend_status():
    records = [_row("2026-05-04")] + [_row("2026-05-11")] * 3
    stats = compute_weekly_stats("THM-001", records)
    assert stats[1]["trend_status"] == "growing"
    assert stats[1]["percent_change"] > 20


def test_declining_trend_status():
    records = [_row("2026-05-04")] * 4 + [_row("2026-05-11")]
    stats = compute_weekly_stats("THM-001", records)
    assert stats[1]["trend_status"] == "declining"
    assert stats[1]["percent_change"] < -20


def test_stable_trend_status():
    records = [_row("2026-05-04")] * 5 + [_row("2026-05-11")] * 5
    stats = compute_weekly_stats("THM-001", records)
    assert stats[1]["trend_status"] == "stable"


def test_weekly_counts_and_distributions():
    records = [
        _row("2026-05-04", sentiment="Negative"),
        _row("2026-05-05", sentiment="Positive"),
    ]
    stats = compute_weekly_stats("THM-001", records)
    assert len(stats) == 1
    assert stats[0]["feedback_count"] == 2
    assert stats[0]["sentiment_distribution"] == {"Negative": 0.5, "Positive": 0.5}


def test_weeks_are_bucketed_monday_start():
    # 2026-05-04 is a Monday, 2026-05-10 is the following Sunday -> same week
    records = [_row("2026-05-04"), _row("2026-05-10")]
    stats = compute_weekly_stats("THM-001", records)
    assert len(stats) == 1
    assert stats[0]["week_start"] == "2026-05-04"
