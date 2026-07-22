# 0016 — Classification pipeline: JSONL logging + Postgres storage

**Date**: 2026-07-22
**Status**: Complete

## What changed

Addressed mentor review feedback on the classification pipeline (`scripts/pipeline/run_llm.py`):
no logging, and results written to CSV/JSON files instead of Postgres.

- **Structured logging** (`src/logging_utils.py`, new): `get_jsonl_logger(name, path)` builds a
  `logging.Logger` with a `FileHandler` (append mode) and a bare `%(message)s` formatter,
  `propagate=False` so it doesn't also print through the console handler. `FewShotClassifier
  .classify()` (`src/classification/classifier.py`) logs one JSON line per classification -
  cache-hit, fresh success, and failure paths all covered - via a module-level
  `logging.getLogger("classification.runs")`. Fields: `record_id`, `model`, `input_tokens`,
  `output_tokens`, `latency_seconds`, `predicted_label`, `cache_hit`, `dry_run`, `error`. The
  classifier only logs by name (stays IO-agnostic); `run_llm.py` attaches the file handler at
  startup, writing to `results/logs/classification_runs.jsonl`. `print()` calls in
  `run_llm.py`/`run_evaluation.py` replaced with `logging.basicConfig` + module loggers.
- **`evaluation_runs` table** (`app/models/evaluation.py`, `app/repositories/evaluation.py`,
  migration `e1fe37c50385`): one row per gold-set evaluation run - `model_name`, `dry_run`,
  `scored_count`, `total_gold_count`, `metrics_json` (field-level accuracy/precision/recall/F1
  from `evaluate_predictions()` plus run-level stats from `summarize_run()` - both pre-existing
  functions in `src/classification/evaluator.py`, unchanged). Mirrors `Report`'s JSON-column
  pattern rather than exploding every metric into its own column.
- **`run_llm.py` rewired to Postgres**: opens one `SessionLocal()`, keeps the existing
  gold/non-gold CSV-based dataset loading (that's test-set selection, not storage) and
  `classifier.classify()` loop unchanged, but now persists each successful classification as an
  `AnalysisResult` row (`analysis_repo.create`) and flips `feedback.processing_status =
  "processed"` - same fields/`model_name` convention `analysis_service.analyze_feedback()`
  already uses for the live API - then writes one `EvaluationRun` row summarizing the whole run.
  Single commit at the end (`try`/`rollback`/`finally close`, same pattern as
  `scripts/import_data.py`). The old `results/llm_predictions.csv`, `llm_failures.json`,
  `llm_run_meta.json` writes are removed entirely.
- **`run_evaluation.py`**: LLM branch now reads the latest `evaluation_runs` row
  (`evaluation_repo.get_latest`) instead of `llm_predictions.csv`; baseline branch is unchanged
  (still reads `results/baseline_predictions.csv` - out of scope for this pass, see Follow-ups).
- `backend/results/logs/` added to the root `.gitignore` (generated telemetry, same treatment
  as `backend/results/cache/`).

## Why

Mentor review (2026-07-22): "Add logging... I don't see any in the pushed code... Every
classification run should log record ID, model used, token count, latency, predicted label, and
whether it was a cache hit or a live call. Write to a file in JSON Lines format." and "Phase 3 of
your pipeline should store results in Postgres instead of CSVs. Three tables: feedback (raw
input), analysis_results (LLM output), evaluation_runs (per-run metrics)." `feedback` and
`analysis_results` already existed from the Phase 5 backend work (`0010-*.md`) and are used by
the live API - the actual gap was that the standalone pipeline script never wrote to them, plus
the missing `evaluation_runs` table.

## Files changed

```
backend/src/logging_utils.py                                  (new)
backend/app/models/evaluation.py                               (new)
backend/app/repositories/evaluation.py                         (new)
backend/alembic/versions/e1fe37c50385_add_evaluation_runs_table.py  (new)
backend/app/models/__init__.py                                 (import EvaluationRun)
backend/src/classification/classifier.py                       (JSONL logging in classify())
backend/scripts/pipeline/run_llm.py                             (Postgres storage, logging)
backend/scripts/pipeline/run_evaluation.py                      (LLM branch reads Postgres)
.gitignore                                                      (backend/results/logs/)
```

## Results

- `python scripts/pipeline/run_llm.py` (dry-run): 30/30 gold records classified, 30
  `analysis_results` rows + 1 `evaluation_runs` row written, 30 JSONL lines in
  `results/logs/classification_runs.jsonl` (all valid JSON, verified).
- `python scripts/pipeline/run_evaluation.py`: `llm` section of the printed report now sourced
  from the `evaluation_runs` row, `baseline` section unchanged.
- `pytest`: 186/186 passing (run from the host venv against `flowhub_test` - running it inside
  the `backend` container fails because that container's network can't reach
  `localhost:5433/flowhub_test`, a pre-existing test-infra detail unrelated to this change).

## How to verify

```bash
cd backend
docker compose up -d db
alembic upgrade head
python3 scripts/pipeline/run_llm.py
psql "$DATABASE_URL" -c "select count(*) from analysis_results;" \
                     -c "select * from evaluation_runs order by created_at desc limit 1;"
tail -3 results/logs/classification_runs.jsonl
python3 scripts/pipeline/run_evaluation.py
python3 -m pytest -q
```

## Notable decisions

- **`run_llm.py` builds its own `AnalysisResult` instead of calling
  `analysis_service.analyze_feedback()`.** That service function re-runs
  `classifier.classify()` internally and returns only the persisted `AnalysisResult`, discarding
  the per-call telemetry (`latency_seconds`, tokens, `retries`, `from_cache`) that
  `summarize_run()` needs for the `evaluation_runs` row. `run_llm.py` already has that telemetry
  from its own `classify()` call, so it persists directly - a small, deliberate duplication of
  ~10 lines rather than losing that data.
- **One `AnalysisResult` row per invocation, regardless of cache hit** - same behavior as
  calling the live API's analyze endpoint twice on the same feedback id (append-only history is
  the model's existing design, documented on `AnalysisResult` itself), not a new behavior
  introduced here.
- **`metrics_json` computed once, in-process, from the in-memory `ClassificationResult` list** -
  not reconstructed later from `analysis_results` - because `AnalysisResult` has no
  `retries`/`latency`/`cache_hit`/`error` columns and failed classifications are never inserted,
  so that data only exists at the moment the run happens.

## Follow-ups deferred

`run_baseline.py` and the baseline half of `run_evaluation.py` still use
`results/baseline_predictions.csv` - folding the rule-based baseline arm into Postgres too
(and resolving the "latest analysis per feedback_id across multiple models" ambiguity that
would introduce) is a separate pass, not attempted here. SQLAlchemy-for-CRUD /
`text()`-for-aggregations convention (also from the same mentor review) not yet applied anywhere
new since no aggregation/dashboard query work was in scope this pass.
