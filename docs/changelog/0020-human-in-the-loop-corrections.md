# 0020 — Human-in-the-loop classification corrections

**Date**: 2026-07-22
**Status**: Complete (backend only - no frontend UI yet)

## What changed

Added the ability to correct a single classification field (`feedback_type`, `category`,
`product_module`, `sentiment`, `urgency`) on a feedback record, recorded as an audit trail and
fed back into the LLM classifier's few-shot examples.

- **`app/models/correction.py`** (new): `corrections` table - append-only, one row per
  correction (`feedback_id`, `field`, `original_value`, `corrected_value`, `corrected_by`,
  `created_at`).
- **`alembic/versions/b9f4d21a7c58_...`**: migration, applied.
- **`app/schemas/correction.py`**: `CorrectionRequest` validates `corrected_value` against the
  same allowed literal set as the classifier output for that field (rejects e.g.
  `sentiment: "Furious"` with a 422). `CorrectionStatsOut` for the accuracy signal below.
- **`app/services/analysis_service.py`**:
  - `correct_classification()` - writes the `Correction` audit row, then writes a *new*
    `AnalysisResult` row (same append-only convention as reprocessing) copying the latest
    analysis with the one field overridden, `model_name="human_correction"`,
    `confidence=1.0`. The live classification reflects the fix immediately.
  - `get_correction_stats()` - correction rate overall and per-field, computed from stored
    data (raw SQL-style aggregation via SQLAlchemy Core `select`/`func`, no ORM `.query()`).
  - `_correction_few_shot_examples()` - turns recent corrections into few-shot examples (post-
    correction classification as the target output) and merges them with the static example
    pool on every LLM classification call, so the classifier stops repeating a mistake a human
    already fixed. Dropped the old module-level classifier cache (`_llm_classifier`) since the
    example set must reflect the latest corrections on every call; only the static base
    example pool is still cached.
- **`app/api/routes/analysis.py`**: `PATCH /analysis/{feedback_id}/classification`,
  `GET /analysis/{feedback_id}/corrections` (audit trail), `GET /analysis/corrections/stats`.

## Why

Item 1 of the rereflect-inspired feature set the user asked for: a correction loop so the
classifier improves from human feedback rather than repeating the same mistakes indefinitely.

## Verification

- `alembic upgrade head` → migration applied cleanly.
- `.venv/bin/python -m pytest tests/api/test_analysis.py -q` → 15/15 passed (5 new: correct/
  reject-invalid/404-without-prior-analysis/audit-trail/stats).
- `.venv/bin/python -m pytest tests/ -q` (full suite, host venv against mapped test DB) →
  198 passed, 1 pre-existing unrelated failure (`test_health.py::test_status_reports_
  database_connected`, a dev-vs-test `DATABASE_URL` environment mismatch, not caused by this
  change).

## Notable decisions

- No frontend UI in this pass - there's no feedback detail page yet (`FeedbackTable` links to
  `/feedback/{id}`, which doesn't exist) to hang a correction control off of. Scoped to backend
  + API to keep this phase fast; UI is a natural follow-up once a detail page exists.
- Corrections are per-field, not a full re-classification - matches the actual UI affordance
  this enables (fix the one thing that's wrong) and keeps the audit trail granular (one row per
  field corrected, not one blob per correction event).
- Rebuilding the `FewShotClassifier` on every LLM call (rather than caching it) trades a small,
  one-time-per-call constructor cost (loads a local JSON cache file, no network) for guaranteeing
  corrections are never stale - acceptable since the LLM call itself already dominates latency.
