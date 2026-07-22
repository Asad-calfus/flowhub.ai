# 0011 — Phase 6: Weekly Insight Report Generation

**Date**: 2026-07-21
**Status**: Complete

## What changed

Added `backend/src/reports/` (deterministic analytics + optional LLM narrative generation)
and `backend/app/api/routes/reports.py` (persisted via a new `reports` table), producing a
weekly customer-feedback report from data already computed in Phases 1-5. No counts,
percentages, or trends are ever calculated by an LLM - see Notable decisions.

- **Schemas** (`src/reports/schemas.py`): `ReportingPeriod`, `SummaryMetrics`,
  `ThemeInsight`/`ProductModuleInsight`/`ContextInsight`/`EnterpriseInsight`/
  `RecommendedAction` (each carrying a `SupportingEvidence` block - representative feedback
  IDs, related context/theme IDs, an evidence-strength label), and the top-level
  `WeeklyReport` covering all 12 required sections. A separate, deliberately narrower
  `EvidencePack`/`LLMReportNarrative` pair is the *only* thing an LLM ever sees or produces -
  the narrative schema has no numeric fields at all, so it is structurally impossible for a
  model to "calculate" or "change" a value (see Notable decisions).
- **Aggregator** (`src/reports/aggregator.py`): SQL + deterministic Python over
  `feedback`/`analysis_results`/`theme_members`/`context_matches`/`context_records` for a
  `[start_date, end_date]` window plus optional `product_module`/`customer_tier` filters -
  totals, by-source/type/module/tier distributions, sentiment distribution, per-theme and
  per-context (known bug/feature request/release) current-vs-previous-period counts and
  trend status (reusing `src.themes.trends`' growth/decline thresholds, not duplicating
  them), new-untracked-issue detection (derived from stored `ContextMatch.match_status` +
  `LOW_SIGNAL_THRESHOLD`, reused from `src.retrieval.context_retriever`), Enterprise-tier
  negative feedback, low-confidence classifications, and rule-based recommended actions
  (`_derive_recommended_actions` - six fixed rules, e.g. a known bug with ≥3 matched reports
  this period and a growing/new trend → `review_bug_priority`).
- **Evidence builder** (`src/reports/evidence_builder.py`): shapes the aggregator's output
  into a compact `EvidencePack` - top 8 themes, top 5 context items per section, 2-3
  representative feedback previews per insight (`MAX_THEMES`/`MAX_CONTEXT_PER_SECTION`/
  `MAX_REPRESENTATIVES` in `schemas.py`). No raw feedback beyond the sampled representatives
  ever leaves this module.
- **Generator** (`src/reports/generator.py`): `generate_deterministic_report` builds report
  prose from templates (no LLM, no API key needed - the cost-free default and evaluation
  baseline). `LLMReportGenerator` mirrors the Phase 2 `FewShotClassifier` pattern - dry-run
  by default, one retry on invalid JSON *or* an unsupported ID reference
  (`validate_narrative_ids`/`UnsupportedReferenceError`), local disk cache keyed by a hash of
  the evidence pack, dry-run stub reuses the deterministic templates so the parse/validate
  path is always exercised even with no API key. `assemble_report` is the single place a
  narrative's text and the evidence pack's numbers are merged - numeric fields are always
  copied from the pack, never read from the narrative. `render_markdown` produces the
  Markdown report from a finished `WeeklyReport`.
- **Evaluator** (`src/reports/evaluator.py`): deterministic checks only (no LLM judge) -
  metric correctness (report metrics == evidence pack metrics), evidence traceability
  (representative feedback IDs are a subset of what the pack sampled for that entity),
  unsupported-claim count (insights with no evidence reference at all), theme/important-issue
  coverage, recommendation support rate, schema success. Human-scored fields (correctness,
  clarity, usefulness, evidence quality, actionability, 1-5) are left as `None` placeholders
  for manual rubric entry.
- **Persistence** (`app/models/report.py`, migration `d4f16d65c594`): one `reports` row per
  generation (immutable history, same convention as `analysis_results`) - period, filters,
  generation method/model/prompt version, full `evidence_json` + `report_json`, rendered
  `markdown`, timestamp.
- **APIs** (`app/api/routes/reports.py`): `POST /api/v1/reports/weekly` (`start_date`,
  `end_date`, `mode`: `deterministic`|`dry_run`|`live`, optional `product_module`/
  `customer_tier` filters, `force`), `GET /api/v1/reports` (paginated summaries), `GET
  /api/v1/reports/{id}`. Same cost-safety contract as `POST /api/v1/analysis/{id}`:
  `mode=live` returns `503` immediately if no provider API key is configured.
- **Scripts** (`scripts/pipeline/generate_weekly_report.py`, `evaluate_weekly_report.py`):
  CLI wrappers over the same service used by the API - deterministic/dry-run/live modes,
  live mode prints a rough cost estimate and asks for confirmation before spending (same
  pattern as `scripts/pipeline/run_llm.py`).
- **Tests** (51 new: `backend/tests/reports/`, `backend/tests/api/test_reports.py`):
  date-range filtering, aggregation correctness, negative-ratio percentage, week-over-week
  trend classification (growing/new/stable), enterprise/new-issue/low-confidence detection,
  recommended-action rule triggers, empty-period behavior, evidence-pack size limits,
  deterministic-report number fidelity, unsupported-reference rejection, LLM retry/cache/
  force/dry-run behavior (mirroring the Phase 2 classifier test suite), evaluator metrics,
  API creation/retrieval/listing/persistence, live-without-key 503.

## Why

Phase 6 of `docs/project_plan.md` - turn the stored analytics, themes, sentiment, context
matches, and representative feedback from Phases 1-5 into a weekly report a human can act
on, with the LLM (when used) restricted to explaining already-computed evidence rather than
generating any of the numbers itself.

## Files changed

```
backend/src/reports/                                      (new)
backend/app/models/report.py, app/repositories/report.py   (new)
backend/app/schemas/report.py, app/services/report_service.py  (new)
backend/app/api/routes/reports.py                          (new)
backend/app/api/router.py                                   (registers reports.router)
backend/app/models/__init__.py                               (imports Report)
backend/alembic/versions/d4f16d65c594_add_reports_table.py  (new)
backend/scripts/pipeline/generate_weekly_report.py, evaluate_weekly_report.py  (new)
backend/tests/reports/, tests/api/test_reports.py            (new, 51 tests)
backend/results/reports/weekly_report.json, weekly_report.md,
  report_evaluation.json, report_error_analysis.md           (new)
README.md, PROJECT_CONTEXT.md, docs/project_plan.md, backend/README.md, CHANGELOG.md
```

## Results

- **Deterministic report** (`RPT-0004`, period 2026-05-04..2026-05-10, 11 feedback records):
  6 themes, 1 known bug and 1 feature request with repeated reports, 1 new-untracked-issue
  cluster, 0 Enterprise-tier negative reports, 0 recommended actions (none crossed the
  `MIN_REPEAT_COUNT=3` threshold in this sparse period). Full report:
  `backend/results/reports/weekly_report.md`.
- **Evaluation**: `metric_correctness=True`, `theme_coverage=1.0`,
  `important_issue_coverage=1.0`, `evidence_traceability_rate=1.0`,
  `unsupported_claim_count=0`, `recommendation_support_rate=1.0`, `schema_success=True` - all
  expected to be perfect for the deterministic path by construction; see
  `report_error_analysis.md` for what these numbers do and don't tell you, plus the
  systemic data-coverage limitation they surface (most non-gold feedback still has no stored
  classification/context-match, so most periods will show it as "not yet processed" rather
  than double-counting it).
- **Tests**: 182/182 passing (131 pre-existing + 51 new).

## How to verify

```bash
cd backend
python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10
python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10 --mode dry-run
python3 scripts/pipeline/evaluate_weekly_report.py
python3 -m pytest tests/reports tests/api/test_reports.py -q   # 51 passed
python3 -m pytest -q                                            # 182 passed
```

## Notable decisions

- **LLM narrative schema has zero numeric fields.** Rather than trusting an LLM to "not
  change" counts/percentages/trends it was given, `LLMReportNarrative` simply has nowhere to
  put a number - every field is `title`/`description` text keyed by an ID that must already
  exist in the `EvidencePack`. `assemble_report` always copies `feedback_count`/`trend`/
  `percent_change`/`sentiment_distribution` from the pack, never from the narrative. This
  makes "the LLM must not invent metrics or change calculated values" a schema-level
  guarantee rather than a prompt instruction to hope the model follows.
- **Unsupported-reference prevention via post-hoc ID validation, not prompt trust alone.**
  `validate_narrative_ids` checks every `theme_id`/`context_id`/`action_id` the model
  returned against the sets actually present in the evidence pack; a mismatch raises
  `UnsupportedReferenceError`, which `LLMReportGenerator.generate` treats exactly like
  invalid JSON - one retry, then a recorded failure. Same one-retry contract as the Phase 2
  classifier.
- **`aggregator.py`/`evidence_builder.py` depend on `app.models`/SQLAlchemy `Session`,
  unlike Phases 1-4's file-based `src/` packages.** Phase 6 is fundamentally a query over
  persisted Postgres data (feedback/analysis/theme/context tables introduced in Phase 5),
  not a standalone local pipeline - there's no CSV/`.npy` equivalent to compute this from.
  Keeping it in `src/reports/` (rather than inline in `app/services/`) still keeps the
  aggregation/generation logic out of the API route, per the project's "no analytics logic
  in routes" rule; it just accepts a `Session` parameter instead of only plain dicts.
- **New-untracked-issue detection reuses stored `ContextMatch` rows, not live retrieval.**
  Recomputing `get_context_matches` for every feedback in a period would mean the report
  generator does its own embedding/similarity work - instead, the aggregator classifies a
  feedback record as "new/untracked" only if it already has `context_match` rows with no
  `matched` status and a best score below `LOW_SIGNAL_THRESHOLD` (mirroring
  `retrieval_service.get_context_matches`'s status logic exactly, imported not duplicated).
  Feedback with *no* context_match rows at all (not yet retrieval-processed) is excluded from
  both the "new issue" count and the "matched" counts, and surfaced instead as a data
  limitation - see `report_error_analysis.md`.
- **Recommended actions are pure rule-based, wording is the only thing an LLM may touch.**
  `_derive_recommended_actions` decides `action_type`/`priority`/which evidence IDs are
  attached; `LLMReportNarrative.action_narratives` may only supply `title`/`description` text
  for an `action_id` that already exists - it cannot add, remove, or reclassify an action.

## Follow-ups / deferred (Phase 7+)

Frontend, Celery/Redis, authentication, and scheduled/automatic weekly report generation
were explicitly out of scope for this phase (per the task spec) and remain deferred to
Phases 7-8 in `docs/project_plan.md`. Also deferred, noted in
`report_error_analysis.md`: giving "new" themes their own report section separate from
"growing," and a live LLM run's latency/token/cost numbers (no `--live` call has been made
against this dataset yet - cost-safety default, same as Phase 2/3).
