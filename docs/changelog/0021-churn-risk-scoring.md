# 0021 — Churn risk scoring

**Date**: 2026-07-22
**Status**: Complete (backend only - no frontend UI yet)

## What changed

Added a rule-based, deterministic churn risk score per customer - no LLM, no trained model,
same "explainable numbers first" philosophy as the weekly report aggregator.

- **`src/churn/scoring.py`** (new): pure scoring function. `risk_score` (0-100) = a weighted
  blend of `negative_ratio` (0.5), `high_urgency_ratio` (0.3), and whether the customer's
  *most recent* feedback was negative (0.2) - a fresh negative signal matters more than old
  negativity buried in a longer history. `risk_level` bands: High >=70, Medium >=40, else Low.
- **`app/services/churn_service.py`** (new): raw-SQL aggregation (GROUP BY + a
  `DISTINCT ON`/window-style CTE for "most recent feedback per customer"), per the
  SQLAlchemy-for-CRUD/`text()`-for-aggregations convention - feeds the pure scorer above.
- **`app/schemas/churn.py`**, **`app/api/routes/churn.py`** (new): `GET /churn/customers`
  (ranked, highest risk first), `GET /churn/customers/{customer_id}`.
- **`app/api/router.py`**: registered the new router.

No migration - the score is computed on the fly from existing `feedback`/`analysis_results`
data, nothing new to store.

## Why

Item 2 of the rereflect-inspired feature set: surface at-risk customers from signals already
in the data (sentiment, urgency, recency) without adding a new pipeline.

## Verification

- `.venv/bin/python -m pytest tests/churn tests/api/test_churn.py -q` → 8/8 passed (4 pure
  scoring-function tests, 4 API tests including ranking order and 404-for-unknown-customer).
- `.venv/bin/python -m pytest tests/ -q` (excluding the two pre-existing unrelated failures
  from earlier phases) → 205 passed.

## Notable decisions

- Tier is returned as metadata, not folded into the score itself - conflating "likelihood of
  churn" with "business impact of losing them" would make the score harder to reason about.
  Prioritization by tier can be a client-side sort on top of `risk_score`.
- No frontend UI in this pass, same reasoning as [[0020]](0020-human-in-the-loop-corrections.md) -
  no customer-facing page exists yet to hang it on; scoped to backend + API for speed.
