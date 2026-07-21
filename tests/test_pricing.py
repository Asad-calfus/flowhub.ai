from src.classification.pricing import estimate_cost_usd, estimate_run_cost_usd


def test_estimate_cost_known_model():
    cost = estimate_cost_usd("gpt-4o-mini", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 0.15 + 0.60


def test_estimate_cost_unknown_model_returns_none():
    assert estimate_cost_usd("some-made-up-model", 1000, 1000) is None


def test_estimate_run_cost_scales_with_record_count():
    cost_10 = estimate_run_cost_usd("gpt-4o-mini", n_records=10)
    cost_20 = estimate_run_cost_usd("gpt-4o-mini", n_records=20)
    assert cost_20 == cost_10 * 2


def test_estimate_run_cost_for_30_gold_records_is_a_few_cents_or_less():
    cost = estimate_run_cost_usd("gpt-4o-mini", n_records=30)
    assert cost is not None
    assert cost < 0.05
