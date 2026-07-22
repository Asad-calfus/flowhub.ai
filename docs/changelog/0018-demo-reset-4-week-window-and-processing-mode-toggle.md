# 0018 — Demo reset with a rolling 4-week window, local/API processing toggle, OpenAI default

**Date**: 2026-07-22
**Status**: Complete

## What changed

### 1. Feedback dates now span a rolling 4 weeks, not ~6 months

`backend/scripts/data/generate_dataset.py` previously hand-authored `created_at` timestamps
spread from January to July 2026. Added `_rescale_created_at_dates()`, which re-maps every
record's date (in original chronological rank order, so the narrative arcs are preserved) into
a `WINDOW_DAYS = 28` window ending **today**, keeping the original time-of-day. Every
re-generation is "fresh" relative to whenever it's run, and the ~150 records land roughly
evenly across 4 calendar weeks (~14-39/week) instead of a thin, uneven 6-month spread - the
weekly report's week-over-week comparisons now have comparable-sized buckets.

### 2. `backend/scripts/reset_demo.py` (new)

Wipes workspace_id="demo" only (feedback + cascaded analysis/embeddings/context-matches/theme
memberships, plus themes and reports) - other workspaces (anonymous browser sessions, e2e test
runs) are untouched. Reseeds from the regenerated CSV, reimports cached embeddings and context
matches (no recomputation needed - feedback text is unchanged, so the existing embedding cache
still hash-matches), then runs the free local pipeline end-to-end: baseline classification for
all 150 records + theme recompute. No LLM calls.

Used once against the shared dev DB: workspace `demo` reset from 357 accumulated
feedback rows (207 from repeated manual CSV uploads during earlier testing) down to a clean
150, dated 2026-06-25 to 2026-07-22, 16 themes, 0 stale reports.

### 3. Fixed a real bug in `theme_service.recompute_themes`

Found while re-running theme clustering against the reset demo data: `theme_repo.next_id()`
queries `MAX(Theme.id)`, but `SessionLocal` is `autoflush=False`
(`backend/app/core/database.py`), so calling it in a loop without an explicit flush meant every
theme created in one `recompute_themes()` call got the **same** id - failing with a
`UniqueViolation` on the final flush the moment clustering produced more than one theme (the
normal case). This wasn't caught before because the only themes that existed in the demo
workspace came from the legacy CSV-based import path (`import_service._import_themes`, which
assigns ids from the CSV directly), not from this live recompute path - the other workspace
that *did* go through "Process my data" via the UI had 100 feedback records and **zero**
themes, silently failing. Fixed with a `db.flush()` right after each `db.add(Theme(...))`.

### 4. Local vs. OpenAI-API processing toggle (frontend)

`AnalysisRequest`/`BatchAnalysisRequest` (`method`, `live`) and `ReportGenerationRequest`
(`mode`) already supported this at the API layer (baseline/dry-run vs. real LLM call), but
neither was exposed as a user-facing choice - the "Get started" page always called
baseline/free, and `ReportGenerationForm` hardcoded `mode: "deterministic"` with a note saying
live wasn't exposed.

- **`GET /api/v1/status`** (`backend/app/api/routes/health.py`) now also returns
  `llm_provider`, `llm_model`, `llm_configured` (whether an API key is present for the
  configured provider) - never the key itself.
- **`ProcessingModeToggle`** (new, `frontend/components/ProcessingModeToggle.tsx`): a shared
  "Local (free)" vs. "OpenAI API key" control. Fetches `/status` once to disable the API option
  (with an explanatory tooltip) when no key is configured, so a user can never trigger a paid
  call the backend would reject anyway.
- Wired into `frontend/app/get-started/page.tsx` (classification: `method`/`live`) and
  `frontend/components/ReportGenerationForm.tsx` (report narrative: `mode`).
- `api.runBatchAnalysis()` now takes `(method, live)` instead of always posting `{}`.

### 5. Switched the configured provider to OpenAI's `gpt-4o-mini`

`backend/.env` had `LLM_PROVIDER=groq` / `llama-3.1-8b-instant` left over from
[[0017]](0017-groq-classifier-provider.md)'s test run. User provided a real `OPENAI_API_KEY`
and asked for "a model that will not cost too much but efficient" - switched to
`LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` (already the documented cost-efficient default
in `.env.example` and `src/classification/pricing.RECOMMENDED_MODEL`). Verified end-to-end with
one real, forced live call (`POST /analysis/FB-0001 {"method":"llm","live":true,"force":true}`)
→ `model_name: "openai:gpt-4o-mini"`, then reset that one record back to baseline so the reset
demo stays fully local/consistent by default.

## Why

User wanted the demo data reset and re-dated so week-over-week numbers in the weekly report are
meaningful ("good number to compare"), plus an explicit choice between free local processing and
real OpenAI calls now that a real key is available, done in a cost-safe way consistent with
[[feedback_openai_cost_safety]] (opt-in, never silently spends, cheap model).

## Verification

- `docker exec backend python scripts/data/generate_dataset.py` → 150 records,
  dates 2026-06-25→2026-07-22.
- `docker exec backend python scripts/reset_demo.py` → 150 feedback/analysis, 16 themes, 0
  reports, weekly counts 20/38/39/39/14.
- `docker exec backend python -m pytest tests/ -q` → 100 passed (the 88 API/integration
  errors are a pre-existing `flowhub_test` DB connectivity gap in this dev environment,
  unrelated to this change - confirmed by running the DB-independent suites
  (`tests/themes`, `tests/classification`, `tests/retrieval`) standalone: 100/100 passed).
- `npx tsc --noEmit` in `frontend/` → clean.
- Manual: `GET /api/v1/status` reflects the new provider/model; one real OpenAI call verified
  the "API key" path actually works end-to-end.

## Notable decisions

- Rescaled dates by **chronological rank**, not a proportional stretch of the original deltas -
  a straight stretch would have compressed multi-day bug-report arcs into the same few hours,
  which reads oddly in a demo. Rank-based spacing keeps the story's ordering intact while
  giving even weekly buckets.
- Reset script skips reimporting the legacy `results/themes/*.csv` and
  `results/baseline_predictions.csv` pipeline outputs (Phase 1-4 CSV artifacts) - those predate
  the date rescale and would show stale trend windows. Recomputes themes and classifies fresh
  from Postgres instead, which is also what the live "Process my data" flow does.
- Left `context_records` (bugs/feature requests/releases/modules) untouched - they're shared
  reference data, not workspace-scoped, and their dates are historical ("already happened
  before this week's feedback"), not something the 4-week rescale needs to touch.
- Did not commit any of this - there's a large amount of pre-existing uncommitted work in the
  repo from prior sessions (Phase 6/7, reports, themes, the entire frontend); bundling this in
  wasn't asked for.
