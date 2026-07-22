# 0019 — All-time report mode (whole-dataset aggregation, no date filter)

**Date**: 2026-07-22
**Status**: Complete

## What changed

Weekly reports previously *required* `--start`/`--end` (API: `start_date`/`end_date`) and
filtered every query on `feedback_created_at` within that window. Any feedback with a null
`feedback_created_at` (e.g. a dateless CSV import) was silently excluded, and there was no way
to get one report over the entire dataset. Added an "all-time" mode: omit both dates and the
report aggregates over every feedback record in the workspace, dated or not.

### Backend

- **`src/reports/aggregator.py`**: `aggregate_period(db, start_date, end_date, ...)` now accepts
  `None, None` to mean all-time. `_feedback_rows`/`_summary_metrics_sql` drop the date `WHERE`
  clause entirely in that case (so NULL-dated rows are included, not excluded). A new
  `_all_time_bounds()` computes MIN/MAX `feedback_created_at` for display purposes only (falls
  back to today if the workspace has no dated feedback at all). No previous-period query runs;
  `PeriodAggregate.prev_start_date`/`prev_end_date` become `Optional`, and a new `all_time: bool`
  field drives every trend calculation to report `"all_time"` instead of a period-over-period
  label like `"growing"`/`"new"` (which would misleadingly imply comparison against a
  non-existent baseline). Passing exactly one of `start_date`/`end_date` raises `ValueError`.
- **`src/themes/schemas.py`**: `TrendStatus` gains the `"all_time"` literal (shared with the
  report's `EntityStat.trend`).
- **`src/reports/schemas.py` / `evidence_builder.py`**: `ReportingPeriod.is_all_time: bool`
  threaded through the evidence pack.
- **`src/reports/generator.py`**: executive summary and the Markdown title read "all-time"
  instead of a date range when `is_all_time`; the "growing themes" / "known bugs receiving
  additional reports" sections also match on the new `"all_time"` trend so they aren't silently
  empty in this mode.
- **`app/schemas/report.py`**: `ReportGenerationRequest.start_date`/`end_date` are now
  `Optional[date] = None`, with a validator requiring both-or-neither. `is_all_time` added to
  `ReportSummaryOut`/`ReportOut`.
- **`app/models/report.py`** + **`alembic/versions/a7c3e91f2b6d_...`**: new
  `reports.is_all_time` boolean column (`server_default=false`), since `start_date`/`end_date`
  stay `NOT NULL` (populated from the computed display bounds even in all-time mode) and can't
  by themselves signal "this was an all-time run."
- **`app/services/report_service.py`**: persists `agg.start_date`/`agg.end_date`/`agg.all_time`
  (the aggregator's computed values) rather than the raw, possibly-`None` request fields.
- **`scripts/pipeline/generate_weekly_report.py`**: `--start`/`--end` are now optional; omit
  both for an all-time run from the CLI.

### Frontend

- **`ReportGenerationForm.tsx`**: new "All-time report" checkbox that disables the date inputs
  and skips their required-field validation; submits `start_date`/`end_date` as `null`.
- **`lib/types.ts`**: `ReportGenerationRequest` dates are optional/nullable; `is_all_time` added
  to `WeeklyReport.period` and `ReportSummaryOut`.
- **`app/reports/page.tsx`** / **`app/reports/[id]/page.tsx`**: show "All-time" instead of a
  date range when `is_all_time`.
- **`components/Badges.tsx`**: `TrendBadge` renders the `all_time` trend as "All-time" with a
  neutral style instead of falling through to the raw `all_time` string.

## Why

User wants classification and the reporting pipeline to run over the *whole* dataset - both
when records have no date at all, and even when they do (a full-history report, not just a
period slice). Classification and theme clustering already ran on the whole dataset with no
date filter; the weekly report pipeline was the one place a date range was mandatory.

## Verification

- `alembic upgrade head` inside the `backend` container - migration applied cleanly.
- `.venv/bin/python -m pytest tests/reports tests/api/test_reports.py tests/themes -q` (run
  from the host against the mapped `flowhub_test` DB on `localhost:5433`, not inside the
  container - the container can't reach `localhost:5433` itself) → **88 passed**, 1 pre-existing
  unrelated failure (`test_live_llm_report_without_api_key_returns_503` fails because this dev
  `.env` now has a real `OPENAI_API_KEY` set per
  [[0018]](0018-demo-reset-4-week-window-and-processing-mode-toggle.md) - same failure
  reproduces on `main` without any of this change).
- Added tests: `test_all_time_mode_includes_every_record_regardless_of_date`,
  `test_all_time_mode_reports_all_time_trend_not_new`,
  `test_all_time_mode_rejects_only_one_date_given` (aggregator);
  `test_generate_all_time_report_via_api_omits_dates`,
  `test_report_rejects_only_one_date_given` (API).
- `npx tsc --noEmit` in `frontend/` → clean.
- `npx vitest run tests/ReportGenerationForm.test.tsx` → 8/8 passed (2 new: all-time skips
  validation, all-time submits `null` dates).

## Notable decisions

- Kept `reports.start_date`/`end_date` `NOT NULL` and populated them with the actual min/max
  dated-feedback bounds even in all-time mode, rather than making them nullable - every report
  row still has a meaningful, sortable date range for the reports list, and a separate
  `is_all_time` flag is the actual mode signal.
- Distinguished `"all_time"` from `"new"` as a trend label rather than reusing `"new"` (which
  the code already produces when `previous_count == 0`) - reusing `"new"` would have made every
  entity in an all-time report look like it just appeared, which isn't true.
- Left the `new_issue_clusters` trend (`"new"`, meaning "no confident context match yet") and
  the recommended-action rules for feature requests/releases (no trend gate, just a count
  threshold) unchanged - those aren't period-over-period comparisons, so all-time mode doesn't
  change their meaning. Only added `"all_time"` to the two trend checks that gate on
  growth/newness (`known_bugs` review-priority action, `known_bugs_growing`/`growing_themes`
  report sections).
