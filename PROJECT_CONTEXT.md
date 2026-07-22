# Project Context — FlowHub AI Customer Feedback Intelligence Platform

**Purpose of this doc**: a single entry point summarizing everything built so far, so the
next phase can start without re-reading the whole repo. It's a snapshot/index, not the
authoritative source for any topic - follow the links for detail, and treat this doc as
possibly stale on anything it doesn't link to a source file for.

**Last updated**: 2026-07-21, after `docs/changelog/0013`.

**v1 is complete and frozen as of Phase 7** (2026-07-21): synthetic dataset → classification
→ retrieval → theme clustering → Postgres/FastAPI backend → weekly reports → Next.js
dashboard, all working end-to-end. Phases 8-10 (Celery/Redis, human corrections, deployment/
CI hardening) are an explicit v2, not started - see `docs/project_plan.md`'s "v1 scope
freeze" note.

**Roadmap**: see `docs/project_plan.md` for the full 10-phase plan, MVP scope, deferred
features, and the "changes from the original plan" record. This doc is current status; that
one is where we're headed.

## The product (fictional)

**FlowHub** - a project management / team collaboration SaaS. 8 modules: Authentication,
Dashboard, Task Management, Notifications, Billing, Integrations, Reports, Mobile App.
6 releases (`v2.1.0`-`v2.6.0`, Jan-Jul 2026). Defined in `backend/data/context/*.csv`.

## What exists today

### Phase 1 — Synthetic dataset (`docs/changelog/0001-*.md`)

150 hand-authored feedback records + 30 manually-reviewed gold subset + product context
(15 known bugs, 12 feature requests, 6 releases, 8 modules). Deliberately varied: tone,
length, grammar, 5 non-English records, near-duplicates, similar-wording-different-meaning
pairs, 8 recurring themes (69 of 150 records) for future clustering work.

- Full schema: `docs/dataset/data_dictionary.md`
- Label definitions + ambiguous-case rulings: `docs/dataset/taxonomy.md`
- Design rationale + leakage rule origin: `docs/dataset/dataset_plan.md`
- Current stats: `docs/dataset/dataset_summary.md`
- Regenerate/validate: `backend/scripts/data/generate_dataset.py`, `backend/scripts/data/validate_dataset.py`

### Phase 2 — Classification pipeline (`docs/changelog/0002-*.md`, `0003-*.md`)

Turns raw feedback text into structured output: `feedback_type`, `category`,
`product_module`, `sentiment`, `urgency`, `confidence`, `reasoning`. Two implementations:

- **Rule-based + VADER baseline** (`backend/src/classification/baseline.py`) - deterministic, no
  API calls, exists only as a comparison floor.
- **Few-shot LLM classifier** (`backend/src/classification/classifier.py`) - supports OpenAI (JSON
  mode) and Anthropic, strict Pydantic validation (`backend/src/classification/schemas.py`), one
  retry on invalid output, local caching by `feedback_id`, dry-run stub for cost-free
  iteration.

**Data-leakage rule, enforced in code**: classifier input is restricted to `feedback_text`,
`source`, `customer_tier`, `product_version`, `rating`, `language`.
`assert_no_leakage()`/`ClassifierInput` reject any of `feedback_type`, `category`,
`product_module`, `sentiment`, `urgency`, `theme_hint`, `related_context_id`,
`is_gold_label`, `label_source` if they appear in a payload headed for a prompt. Note
`product_module` is a *target to predict* in Phase 2, even though Phase 1's data dictionary
listed it as an input - that's an intentional change, not a contradiction.

Few-shot examples are drawn only from the 120 non-gold records (`select_few_shot_examples`
raises if a gold record leaks into that pool). Evaluation (`backend/src/classification/evaluator.py`)
runs only against the 30 gold records and computes per-field accuracy, macro P/R/F1, and
confusion matrices, plus run-level stats (schema success rate, retries, failures, latency,
token usage).

**Baseline results** (rule-based + VADER, `backend/results/error_analysis.md`):

| field | accuracy |
|---|---|
| feedback_type | 0.40 |
| category | 0.43 |
| product_module | 0.83 |
| sentiment | 0.27 |
| urgency | 0.43 |

Sentiment is the weakest baseline field - VADER under-reacts to long, matter-of-fact negative
support tickets.

**Live LLM results** (`docs/changelog/0017-*.md`, 2026-07-22, `groq:llama-3.1-8b-instant`, 30/30
gold records, 0 failures) - meaningfully better than baseline on every field except
`product_module` (already near-ceiling on baseline):

| field | accuracy | vs. baseline |
|---|---|---|
| feedback_type | 0.67 | +0.27 |
| category | 0.73 | +0.30 |
| product_module | 0.87 | +0.03 |
| sentiment | 0.60 | +0.33 |
| urgency | 0.60 | +0.17 |

Full field-level precision/recall/F1 and confusion matrices are in the `evaluation_runs` table
(Postgres), not a CSV - see Phase 2 logging note below.

**Cost-safe real-key usage** (`docs/changelog/0003-*.md`, `0017-*.md`): `backend/scripts/pipeline/run_llm.py`
always dry-runs unless `--live` is passed explicitly; `--live` prints a cost estimate
(`backend/src/classification/pricing.py`) and asks for confirmation (skippable with `--yes`).
Supports `openai`, `anthropic`, and `groq` (OpenAI-compatible endpoint) via `LLM_PROVIDER`.
Note: `classify()` checks its local cache *before* checking dry-run/live, so a `--live` run
still serves cached dry-run results unless `--force` is also passed - easy to mistake for a
real run otherwise (see `docs/changelog/0017-*.md`'s "Notable decisions").

**Logging + Postgres storage** (`docs/changelog/0016-*.md`): `run_llm.py` writes structured
JSONL per classification (`backend/results/logs/classification_runs.jsonl` - `record_id`,
model, tokens, latency, cache_hit, dry_run) and persists results directly to Postgres
(`analysis_results` + a new `evaluation_runs` table), not CSV/JSON files.

### Phase 3 — Embeddings and context retrieval (`docs/changelog/0007-*.md`)

Local semantic retrieval (`backend/src/retrieval/`), no LLM: `sentence-transformers/all-MiniLM-L6-v2`
(384-dim, `EMBEDDING_MODEL` env var). Embeds feedback (input fields only - `feedback_text`,
`source`, `customer_tier`, `product_version`, `language`) and product context
(bugs/features/releases), caches vectors with hash-based skip-unchanged. Cosine similarity
finds top-5 similar feedback (all 150 records) and, for the 30 gold records only, top-3
candidate bugs/feature-requests/releases with a threshold-based status
(`known_bug`/`duplicate_feature_request`/`possible_release_issue`/`new_untracked_issue`/
`no_confident_match`). `related_context_id`/`theme_hint` are read only inside
`backend/scripts/pipeline/evaluate_retrieval.py`, never during retrieval itself.

**Results** (gold set): recall@3 = 1.0, MRR = 0.90, recall@1 = 0.83, false-known-issue rate on
genuinely new issues = 0.33. Similar-feedback same-theme precision/recall@5 = 0.66. Full
breakdown, including the specific miss cases: `backend/results/retrieval/retrieval_error_analysis.md`.

### Phase 4 — Theme clustering and trend detection (`docs/changelog/0009-*.md`)

Local, deterministic, no LLM (`backend/src/themes/`): agglomerative clustering (cosine
distance, average linkage) over the Phase 3 feedback embeddings only -
`THEME_DISTANCE_THRESHOLD=0.55`, `THEME_MIN_SIZE=4`, both centralized in
`src/themes/clustering.py`. TF-IDF keywords per theme, top-3 representatives by centroid
similarity, deterministic naming (keywords + dominant module, no LLM), weekly
count/change/sentiment/tier/module trends with a `new`/`growing`/`stable`/`declining`
status (`>±20%` thresholds). `theme_hint` is read only in `src/themes/evaluator.py`, after
clustering has already run.

**Results**: 16 themes from 150 records, 84 assigned / 66 unclustered (44%). Against the 69
`theme_hint` records: cluster purity 0.92, ARI 0.38, NMI 0.70, pairwise P/R/F1
0.85/0.36/0.51, 3 fragmented true themes (Login failures, Confusing billing charges, Mobile
app crashes - all vocabulary-driven splits), 0 mixed/incoherent predicted themes. One
merge error (`THM-001` mixes Login-failure and Mobile-app-crash records - same "logged out"
wording ambiguity Phase 3 flagged for retrieval). All 5 non-English records stay
unclustered, consistent with `all-MiniLM-L6-v2` being English-trained. Full breakdown:
`backend/results/themes/theme_error_analysis.md`.

### Phase 5 — PostgreSQL and FastAPI backend (`docs/changelog/0010-*.md`)

FastAPI app (`backend/app/`) + Alembic migrations (`backend/alembic/`) over PostgreSQL +
pgvector, exposing Phases 1-4 over HTTP with no logic duplicated - services call
`backend/src/classification/`, `backend/src/retrieval/`, `backend/src/themes/` directly.
`app/{api,core,models,schemas,repositories,services}`, thin routes, business logic in
services, DB queries in repositories.

Tables: `feedback` (raw only, reprocessable), `analysis_results` (history, not overwritten),
`embeddings` (`pgvector` `vector(384)`), `context_records` (bugs/features/releases/modules,
unified), `context_matches`, `themes`, `theme_members`. `backend/scripts/import_data.py`
backfills the existing 150 feedback + context + Phase 3/4 results from CSV/JSON/`.npy` files
(no recomputation, no LLM calls, idempotent). API: feedback CRUD + CSV import + filtered
list, analysis (single/batch/get, reusing `classify_baseline`/`FewShotClassifier` unchanged),
retrieval (similar-feedback via pgvector `cosine_distance`, context-matches reusing
`cosine_top_k`), themes (list/detail/feedback). `GET /health`, `GET /api/v1/status`.

**Cost-safety carried over unchanged**: `method=llm` defaults to `live=false`; `live=true`
returns `503` if no provider key is configured - no API path can spend money implicitly.

**Results**: 131/131 tests passing (98 pre-existing + 33 new API tests, isolated
`flowhub_test` DB). Import backfills 150 feedback / 41 context records / 150 embeddings / 30
baseline analysis results (baseline was only ever run on the 30 gold records) / 270
context-match rows / 16 themes / 84 theme members; idempotent on re-run. Docker Compose at
repo root (`db` + `backend`, ports 5433/8001 - 5432/8000 were already taken by another
project's containers on this machine). Full breakdown, including why LLM predictions were
*not* imported (dry-run stub, not a real result) and the representative-feedback scoring
approximation: `docs/changelog/0010-phase5-postgres-fastapi-backend.md`.

### Phase 6 — Weekly insight report generation (`docs/changelog/0011-*.md`)

Turns Phases 1-5's stored data into a weekly report a human can act on (`backend/src/reports/`),
exposed via `POST /api/v1/reports/weekly`, `GET /api/v1/reports`, `GET
/api/v1/reports/{id}` (persisted in a new `reports` table, migration `d4f16d65c594`).

**Every number is computed by SQL/Python, never by an LLM** (`src/reports/aggregator.py`):
totals, by-source/type/module/tier distributions, sentiment, per-theme and per-context
(known bug/feature request/release) current-vs-previous-period counts and trend status
(reusing `src.themes.trends`' growth/decline thresholds), new-untracked-issue detection
(reusing `src.retrieval.context_retriever.LOW_SIGNAL_THRESHOLD` against stored
`ContextMatch` rows, no live retrieval recomputation), Enterprise-tier negative feedback,
low-confidence classifications, and six rule-based recommended-action triggers. This all
feeds a size-bounded `EvidencePack` (top 8 themes, top 5 context items/section, 2-3
representative feedback/insight - `src/reports/evidence_builder.py`).

**Two generation paths** (`src/reports/generator.py`): a template-based deterministic
baseline (no LLM, no API key, the cost-free default and evaluation baseline), and an
optional `LLMReportGenerator` (same dry-run/retry/cache pattern as the Phase 2
`FewShotClassifier`). The LLM path's structured-output schema (`LLMReportNarrative`) has
**no numeric fields at all** - only `title`/`description` text keyed by IDs that must
already exist in the evidence pack (`validate_narrative_ids` rejects invented IDs, same
one-retry-then-fail contract as invalid JSON). `assemble_report` always copies
counts/percentages/trends from the evidence pack, never from the narrative - so "the LLM
must not invent metrics or change calculated values" is a schema/code guarantee, not a
prompt-only promise.

**Cost-safety carried over unchanged**: `mode=deterministic` is the API default;
`mode=live` returns `503` immediately if no provider key is configured, same contract as
`POST /api/v1/analysis/{id}`. CLI: `backend/scripts/pipeline/generate_weekly_report.py`
(`--mode deterministic|dry-run|live`, live prints a cost estimate and confirms first),
`evaluate_weekly_report.py`.

**Results**: sample deterministic report (`RPT-0004`, 2026-05-04..2026-05-10, 11 feedback
records) - 6 themes, 1 known bug + 1 feature request with repeated reports, 1
new-untracked-issue cluster, 0 recommended actions (period too sparse to cross thresholds).
Evaluation (deterministic checks only, no LLM judge): `metric_correctness=True`,
`theme_coverage`/`important_issue_coverage`/`evidence_traceability_rate`/
`recommendation_support_rate` all `1.0`, `unsupported_claim_count=0` - expected to be
perfect by construction for the deterministic path; the real limitation this run surfaces
is data coverage (most non-gold feedback still has no stored classification/context-match -
see Phase 5's note above), not report logic. Full breakdown, including known
report-content limitations (theme cap silently drops themes past 8, "new" vs "growing"
overlap in sparse periods, representative-feedback selection heuristic):
`backend/results/reports/report_error_analysis.md`.

### Phase 7 — Frontend dashboard (`docs/changelog/0012-*.md`)

Next.js (App Router) + TypeScript + Tailwind + Recharts dashboard (`frontend/`) over the
Phase 5/6 API - no new backend logic, no analytics recomputed client-side. Typed API client
(`frontend/lib/api.ts`) with a single error class, loading/empty/error states everywhere,
backend health indicator polling `GET /health` every 30s.

Pages: Overview (total feedback from `GET /feedback`; sentiment/type/module distributions
and top/growing themes, known-bug/feature-request matches, new-untracked-issues from the
*most recent* generated weekly report's `SummaryMetrics` - there's no bulk
analytics-across-all-feedback endpoint, so duplicating that aggregation client-side would've
meant either recalculating it differently than the backend or reading raw CSVs directly,
both explicitly disallowed); Feedback Inbox (paginated, filtered - source/sentiment/
category/module/tier - table, one `GET /analysis/{id}` call per visible row since
category/sentiment/module live on `AnalysisResult`, not `FeedbackOut`); Feedback Detail
(original data / AI analysis / retrieved evidence kept visually separate, plus theme
assignment - found by checking every theme's member list client-side, since no
`GET /feedback/{id}/theme` endpoint exists); Themes list/detail; Weekly Reports list +
deterministic-report generation form + detail (structured view or rendered Markdown via
`react-markdown`, never raw HTML injection); Evaluation (reads `backend/results/*.json`
through a server-side Next.js route, `app/api/evaluation/route.ts` - the one page allowed to
read result files directly per the phase spec - labels dry-run LLM classification results
so they're never shown as real model performance).

Tests (Vitest + RTL, `frontend/tests/`): API-client error handling, feedback table
rendering, filter query-param construction, loading/empty/error states, report-generation
form validation, dry-run labeling.

**Known limitations**: the feedback-detail theme lookup is an O(themes) client-side join
(fine at 16 themes/150 records, not a real endpoint); the Overview page shows an empty
prompt instead of distributions until at least one weekly report exists, since it doesn't
recompute report-style aggregates itself. Full detail: `frontend/README.md`,
`docs/changelog/0012-*.md`.

**CSV import** (`docs/changelog/0013-*.md`): the Feedback Inbox page can now upload a CSV
directly to the existing `POST /api/v1/feedback/import` endpoint (only `feedback_text`
required; dedup-by-`feedback_id`, safe to re-upload) - no new backend logic, no
client-side parsing.

**Visual redesign** (`docs/changelog/0014-*.md`): new Home page at `/` (was the Overview
dashboard, now moved to `/dashboard`), indigo/violet design tokens, icon-based responsive
sidebar, and a full visual pass across every page - inspired by Chattermill/Thematic,
light-only for now. No backend, API contract, or page-logic changes; one new dependency
(`lucide-react`).

### Repo structure tidy (`docs/changelog/0004-*.md`, `0006-*.md`)

`backend/scripts/` split into `backend/data/` and `pipeline/`; `docs/` split into `dataset/` and
`changelog/`; `backend/tests/` mirrors `backend/src/` (`backend/tests/classification/`). This doc lives at
`PROJECT_CONTEXT.md` (root, moved from `docs/` in 0006 to sit alongside `README.md`/
`CHANGELOG.md`). No `pyproject.toml`/CI yet - explicitly deferred, not an oversight. Current
full layout is in the root `README.md` "Project structure" section.

## Process conventions in effect (see memory, not just this doc)

- A dated doc under `docs/changelog/` after every notable change, indexed in `CHANGELOG.md`.
- Regular, scoped git commits (one per notable change) on `main`, pushed to `origin`
  (`github.com/Asad-calfus/flowhub.ai`).
- Generated/disposable files never committed: `.venv/`, `__pycache__/`, `.pytest_cache/`,
  `backend/results/cache/`, `.env` (all in `.gitignore`).
- Real API keys only ever in `.env` (gitignored), never `.env.example`. Live LLM calls are
  opt-in (`--live`), cost-estimated, and confirmed before spending.

## Explicitly NOT built yet (v2)

Celery/Redis background processing, human-correction feedback loop, authentication/
multi-tenancy, scheduled/automatic report generation, CI/CD, and packaging
(`pyproject.toml`) - all pushed to v2 (Phases 8-10) by explicit decision on 2026-07-21, not
forgotten. v1 (Phases 1-7) is otherwise feature-complete - see `docs/project_plan.md`'s "v1
scope freeze" note and each changelog entry's "Follow-ups deferred". (The API layer and
database were in this list through Phase 4; both now exist as of Phase 5. Weekly report
generation was in this list through Phase 5; it now exists as of Phase 6 - manual/on-demand
only, not scheduled. The frontend was in this list through Phase 6; it now exists as of
Phase 7.)

## Quick orientation for a fresh session

1. Read this doc, then `README.md` for exact run commands.
2. If touching the dataset: `docs/dataset/data_dictionary.md` + `docs/dataset/taxonomy.md`
   first.
3. If touching the classifier: `backend/src/classification/schemas.py` first (the leakage
   contract), then `backend/results/error_analysis.md` for known weak points.
4. If touching the API/database: `backend/app/core/database.py` + `backend/app/models/` for
   the schema, `backend/README.md`'s "Phase 5" section for endpoints/commands.
5. If touching weekly reports: `backend/src/reports/schemas.py` first (the `EvidencePack`/
   `LLMReportNarrative` split is the whole "LLM can't touch numbers" contract), then
   `backend/results/reports/report_error_analysis.md` for known weak points.
6. If touching the frontend: `frontend/lib/types.ts` first (hand-kept in sync with the
   backend Pydantic schemas - no generated client yet), then `frontend/README.md`.
7. Run `python3 -m pytest -q` before and after any backend change (182 tests at last count -
   needs `docker compose up -d db` and a `flowhub_test` database, see `backend/README.md`).
   Run `npm test` in `frontend/` before and after any frontend change.
8. Add a `docs/changelog/000N-*.md` entry + `CHANGELOG.md` line, then commit, before
   considering a change done.
