# Backend — FlowHub AI Customer Feedback Intelligence Platform

Python AI/data pipeline. See root `../README.md` for the project overview and
`../PROJECT_CONTEXT.md` for full current-state context. All commands below assume you've
`cd backend` first.

## Structure

```text
data/                   # dataset (raw/processed/evaluation/context) - see data/README.md
results/                # predictions, metrics, error analysis (generated, not hand-written)
├── retrieval/          # Phase 3 outputs (+ cache/, gitignored)
├── themes/             # Phase 4 outputs
└── reports/            # Phase 6 outputs
scripts/
├── data/               # generate/validate the dataset
└── pipeline/           # classification + retrieval + theme + report runners
src/
├── data_loader.py       # shared CSV loading helpers
├── classification/      # schemas, prompt builder, baseline, LLM classifier, evaluator, pricing
├── retrieval/           # schemas, text_builder, embedder, similarity, context_retriever, evaluator
├── themes/              # clustering, keywords, representatives, naming, trends, evaluator
└── reports/             # aggregator, evidence_builder, prompt_builder, generator, evaluator
app/                     # FastAPI application (Phase 5) - api/, core/, models/, repositories/,
                         # schemas/, services/ - see "Phase 5" section below
tests/
├── classification/      # mirrors src/classification/
├── retrieval/           # mirrors src/retrieval/
├── themes/              # mirrors src/themes/
├── reports/              # mirrors src/reports/ (DB-backed, reuses tests/api's test database)
└── api/                 # FastAPI endpoint tests (isolated flowhub_test database)
```

Dataset/taxonomy/pipeline design docs live in root `../docs/`.

## Phase 1 — Synthetic dataset

See `data/README.md` and `docs/dataset/` (`dataset_plan.md`, `taxonomy.md`,
`data_dictionary.md`, `dataset_summary.md`) for the 150-record synthetic feedback dataset,
gold evaluation set, and product context files.

## Phase 2 — Classification and sentiment pipeline

A small pipeline that turns raw feedback text into validated structured output: feedback
type, category, product module, sentiment, and urgency. Two classifiers are implemented for
comparison - a deterministic rule-based + VADER baseline, and a few-shot LLM classifier with
strict Pydantic validation, retry, and local caching.

**Data-leakage rule (enforced in code, see `src/classification/schemas.py`)**: the classifier
only ever sees `feedback_text`, `source`, `customer_tier`, `product_version`, `rating`,
`language`. `product_module`, `feedback_type`, `category`, `sentiment`, `urgency`,
`theme_hint`, `related_context_id`, `is_gold_label`, and `label_source` are evaluation labels
only, and `assert_no_leakage()` raises if any of them reach a prompt payload.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY (or ANTHROPIC_API_KEY) only for a live LLM run
```

### Run the baseline (rule-based + VADER, no API calls, no cost)

```bash
python3 scripts/pipeline/run_baseline.py
```

### Run the few-shot LLM classifier

```bash
# Dry-run - ALWAYS the default, even if an API key is present. No network calls.
python3 scripts/pipeline/run_llm.py

# Live run: real API calls against the 30 gold records only. Prints a cost estimate
# and asks for confirmation before spending anything.
python3 scripts/pipeline/run_llm.py --live

# Live run, skip the confirmation prompt (e.g. non-interactive/CI use)
python3 scripts/pipeline/run_llm.py --live --yes

# Bypass the cache and reclassify everything (combine with --live to force fresh API calls)
python3 scripts/pipeline/run_llm.py --live --force
```

Predictions are cached by `feedback_id` in `results/cache/llm_cache.json`. Without `--force`,
any record with a valid cached prediction is skipped - re-running while debugging never
re-spends API calls. Only the 30 gold records are ever sent to the LLM; `--live` refuses to
run at all if the configured provider's API key isn't set.

### Using a real API key without overspending

The pipeline is designed so a real key is cheap and hard to spend accidentally:

1. **Dry-run is the script default, not just the library default.** `--live` is the only way
   to trigger a real call, regardless of whether a key is in `.env`.
2. **Cost is estimated and confirmed before any call is made.** `--live` prints an estimate
   (`src/classification/pricing.py`) for the records it's about to send, and prompts for `y/N`
   unless `--yes` is passed.
3. **Only 30 records, ever.** Every script targets `data/evaluation/gold_feedback.csv`
   exclusively - there is no code path that sends the full 150-record dataset to an LLM.
4. **Caching makes iteration free.** Once a gold record has a valid cached prediction, it's
   never re-sent unless you pass `--force`. Prompt/logic changes only cost tokens for the
   records actually affected if you clear just those cache entries.
5. **Use a cheap model.** Default recommendation in `.env.example` is `gpt-4o-mini`
   (`LLM_PROVIDER=openai`) - roughly $0.15 / $0.60 per 1M input/output tokens. For 30 short
   feedback records with a ~5-example few-shot prompt, a full `--live --force` run costs a
   fraction of a cent (see `results/evaluation_metrics.json` → `llm.run_summary` for actual
   token counts after a run, or `estimate_run_cost_usd()` for a pre-flight number).
6. **JSON mode reduces wasted retries.** The OpenAI path uses `response_format={"type":
   "json_object"}`, so malformed-JSON retries (which double the token cost of a record) should
   be rare in practice.
7. **Debug with `--dry-run` first, always.** Validate prompt/schema changes against the local
   stub before ever touching `--live`.

### Run evaluation (baseline vs. LLM, against the gold set)

```bash
python3 scripts/pipeline/run_evaluation.py
```

Writes `results/evaluation_metrics.json` (per-field accuracy, macro precision/recall/F1,
confusion matrices, and run-level stats: schema success rate, retries, failures, latency,
token usage) and prints a summary table.

### Run tests

```bash
python3 -m pytest -q
```

### Full pipeline in one go

```bash
python3 scripts/pipeline/run_baseline.py && python3 scripts/pipeline/run_llm.py && python3 scripts/pipeline/run_evaluation.py
```

### Outputs

```text
results/
├── baseline_predictions.csv
├── llm_predictions.csv
├── llm_failures.json         # stored, not skipped, JSON/schema failures
├── llm_run_meta.json         # model/provider/few-shot example IDs used
├── evaluation_metrics.json
└── error_analysis.md
```

## Phase 3 — Embeddings and context retrieval

Local semantic retrieval, no LLM, no API cost: `sentence-transformers/all-MiniLM-L6-v2`
(384-dim, configurable via `EMBEDDING_MODEL`) embeds feedback + bugs/feature-requests/releases
(`src/retrieval/`). Finds similar historical feedback and matches feedback against known
bugs/feature requests using cosine similarity with configurable thresholds
(`CONTEXT_MATCH_THRESHOLD`, `CONTEXT_LOW_SIGNAL_THRESHOLD`) - never using `related_context_id`
as input, only as post-hoc evaluation ground truth.

```bash
python3 scripts/pipeline/generate_embeddings.py     # embed + cache all records
python3 scripts/pipeline/run_similarity_search.py   # similar feedback (all 150) + context match (gold 30)
python3 scripts/pipeline/evaluate_retrieval.py      # recall@1/3, MRR, same-theme P/R@5, etc.
```

Results: `results/retrieval/` (`*_predictions.csv`, `retrieval_metrics.json`,
`retrieval_error_analysis.md`). Current gold-set numbers: context recall@3 = 1.0, MRR = 0.90;
same-theme precision/recall@5 = 0.66. Full breakdown in the error analysis doc.

## Phase 4 — Theme clustering and trend detection

Local, deterministic clustering, no LLM: agglomerative clustering (cosine distance, average
linkage) over the Phase 3 feedback embeddings only (`src/themes/`). TF-IDF keywords,
centroid-based representatives, rule-based naming, and weekly trend stats per theme.
`theme_hint` is read only for evaluation, after clustering has run.

```bash
python3 scripts/pipeline/generate_themes.py    # cluster + keywords + names + trends
python3 scripts/pipeline/evaluate_themes.py    # coverage, purity, ARI, NMI, pairwise P/R/F1

# force regeneration with different clustering config
THEME_DISTANCE_THRESHOLD=0.6 THEME_MIN_SIZE=5 python3 scripts/pipeline/generate_themes.py
```

Results: `results/themes/` (`theme_assignments.csv`, `themes.csv`, `theme_metrics.json`,
`theme_error_analysis.md`). Current numbers: 16 themes from 150 records, 84 assigned / 66
unclustered; cluster purity 0.92, ARI 0.38, NMI 0.70 against the 69 `theme_hint` records.
Full breakdown in the error analysis doc.

## Phase 5 — PostgreSQL and FastAPI backend

FastAPI app (`app/`) over PostgreSQL + pgvector, exposing Phases 1-4 (`src/`) over HTTP.
Routes are thin; business logic lives in `app/services/`, DB queries in `app/repositories/`.
No classification/retrieval/clustering logic is duplicated - services call `src/` directly.

### Setup

```bash
docker compose -f ../docker-compose.yml up -d db   # Postgres 16 + pgvector, localhost:5433
# .env already has DATABASE_URL=postgresql+psycopg://flowhub:flowhub@localhost:5433/flowhub
alembic upgrade head
python3 scripts/import_data.py                     # backfill existing dataset/results
uvicorn app.main:app --reload --port 8001
```

### Database schema

| Table | Purpose |
|---|---|
| `feedback` | Raw feedback only (no generated fields) - reprocessable |
| `analysis_results` | One row per classification run (history, not overwritten) |
| `embeddings` | `pgvector` `vector(384)` per feedback, `sentence-transformers/all-MiniLM-L6-v2` |
| `context_records` | Known bugs, feature requests, releases, product modules (unified, `context_type` discriminator) |
| `context_matches` | One row per feedback↔context candidate pairing, `match_status` matched/candidate |
| `themes` | One row per cluster: name, keywords, size, first/last seen, trend status |
| `theme_members` | feedback↔theme membership; `membership_score` also identifies representatives (top-3) |
| `reports` | One row per generated weekly report (Phase 6, history, not overwritten) - period, filters, evidence/report JSON, markdown |

### API endpoints (`/api/v1`, see `app/api/routes/`)

```
GET    /health                                     liveness, no DB
GET    /api/v1/status                              liveness + DB round-trip

POST   /api/v1/feedback                            create
POST   /api/v1/feedback/import                     bulk-create from uploaded CSV
GET    /api/v1/feedback                             paginated + filtered list
GET    /api/v1/feedback/{id}
DELETE /api/v1/feedback/{id}
GET    /api/v1/feedback/{id}/similar?top_k=5        nearest feedback (pgvector cosine)
GET    /api/v1/feedback/{id}/context-matches?top_k=3  known-bug/feature/release candidates

POST   /api/v1/analysis/{id}                        {"method": "baseline"|"llm", "live": bool, "force": bool}
GET    /api/v1/analysis/{id}                         latest result
POST   /api/v1/analysis/batch                         {"feedback_ids": [...] | omit for all pending, ...}

GET    /api/v1/themes
GET    /api/v1/themes/{id}                            + sentiment distribution, representative feedback, members
GET    /api/v1/themes/{id}/feedback

POST   /api/v1/reports/weekly                         {"start_date", "end_date", "mode": "deterministic"|"dry_run"|"live", ...}
GET    /api/v1/reports                                paginated report summaries
GET    /api/v1/reports/{id}                           full report (structured JSON + markdown)
```

List filters: `source`, `sentiment`, `category`, `product_module`, `customer_tier`,
`processing_status`, `date_from`, `date_to`, `page`, `page_size`.

**Cost-safe by construction, same guarantees as the standalone pipeline**
([[feedback_openai_cost_safety]]): `method=baseline` is the default; `method=llm` defaults to
`live=false` (dry-run stub, no API call); `live=true` returns `503` immediately if no
provider key is configured. No request path can trigger a real LLM call without an explicit
`"live": true` in the body.

### Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Import existing data

```bash
python3 scripts/import_data.py
```

Backfills the 150 feedback records, 8 product modules, 15 bugs, 12 feature requests, 6
releases, cached Phase 3 embeddings, baseline classification predictions, gold-set context
matches, and Phase 4 theme assignments - straight from the existing CSV/JSON/`.npy` files, no
recomputation, no LLM calls. Every row is existence-checked before insert, so it's safe to
run repeatedly; re-running reports `imported: 0` / everything skipped. Prints a summary
(counts per table + any FK-validation errors) - see `docs/changelog/0010-*.md` for a sample
run.

### Tests

```bash
python3 -m pytest -q                # full suite (182 tests: 98 pipeline + 33 API + 51 reports)
python3 -m pytest tests/api -q       # API tests only
```

`tests/api/` runs against an isolated `flowhub_test` Postgres database
(`TEST_DATABASE_URL`, default `postgresql+psycopg://flowhub:flowhub@localhost:5433/flowhub_test`)
- tables are created fresh per test session and truncated after every test, so it never
touches dev data.

### Docker

```bash
docker compose up -d          # from the repo root: db (5433) + backend (8001)
docker compose up -d db       # Postgres only, if running the API locally instead
```

`pgvector`'s `CREATE EXTENSION vector` runs automatically on first boot
(`scripts/db/init_pgvector.sql`). Host ports are `5433`/`8001`, not the defaults `5432`/
`8000`, to avoid colliding with an unrelated project's containers on this machine - see
`docker-compose.yml` if that's not a constraint for you.

### Not yet implemented

Frontend, Celery/Redis, authentication, and multi-tenancy are out of scope for Phase 5 (see
`docs/project_plan.md`). Also deferred: advanced/full-text search on feedback,
async/background batch analysis (synchronous for now, per spec), and CI.

## Phase 6 — Weekly insight report generation

Turns Phases 1-5's stored data into a weekly report (`src/reports/`), exposed over the API
and persisted in a new `reports` table. No count/percentage/trend is ever calculated by an
LLM - see `PROJECT_CONTEXT.md`'s Phase 6 section and `docs/changelog/0011-*.md` for the full
design rationale.

### Report generation flow

```
aggregate_period (SQL + Python, src/reports/aggregator.py)
    -> build_evidence_pack (size-bounded sampling, src/reports/evidence_builder.py)
        -> generate_deterministic_report   (templates, no LLM)
           OR
           LLMReportGenerator.generate     (dry-run stub / real API call, one retry,
                                             disk cache, ID-reference validation)
    -> assemble_report (merges narrative TEXT + evidence pack NUMBERS -> WeeklyReport)
    -> render_markdown -> persisted to `reports` table (evidence_json + report_json + markdown)
```

### Deterministic vs. LLM mode

- `deterministic` (API/CLI default): template-based prose from the evidence pack, no API
  key needed, no cost. Also the evaluation baseline.
- `dry_run`: exercises the full LLM code path (prompt build, JSON parse, Pydantic
  validation, ID-reference check) using a local deterministic stub instead of a real call -
  same idea as the Phase 2 classifier's dry-run mode.
- `live`: a real API call. Returns `503` immediately if no provider key is configured;
  the CLI script prints a rough cost estimate and asks for confirmation first.

### Evidence-building rules

Top 8 themes, top 5 context items (known bugs/feature requests/releases) per section, 2-3
representative feedback previews per insight (`MAX_THEMES`/`MAX_CONTEXT_PER_SECTION`/
`MAX_REPRESENTATIVES` in `src/reports/schemas.py`). No raw feedback beyond the sampled
representatives is ever included in a prompt.

### Evaluation method

Deterministic checks only (`src/reports/evaluator.py`, no LLM judge): metric correctness,
evidence traceability, unsupported-claim count, theme/important-issue coverage,
recommendation support rate, schema success rate. Human-scored fields (correctness, clarity,
usefulness, evidence quality, actionability - 1-5) are left as `None` placeholders for a
person to fill in against `backend/results/reports/weekly_report.md`.

### Commands

```bash
# Deterministic report (no LLM, no cost)
python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10

# Dry-run LLM path (exercises the full LLM code path, no API calls)
python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10 --mode dry-run

# Live LLM report (real API call; prints a cost estimate and asks for confirmation first)
python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10 --mode live

# Optional filters
python3 scripts/pipeline/generate_weekly_report.py --start ... --end ... --module Dashboard --tier Enterprise

# Evaluate the most recent (or a specific) report
python3 scripts/pipeline/evaluate_weekly_report.py
python3 scripts/pipeline/evaluate_weekly_report.py --report-id RPT-0004

# Tests
python3 -m pytest tests/reports tests/api/test_reports.py -q   # report tests only
python3 -m pytest -q                                            # full suite
```

### API endpoints

```
POST /api/v1/reports/weekly   {"start_date": "2026-05-04", "end_date": "2026-05-10",
                                "mode": "deterministic"|"dry_run"|"live",
                                "product_module": str | null, "customer_tier": str | null,
                                "force": bool}
GET  /api/v1/reports                       paginated report summaries
GET  /api/v1/reports/{id}                  full report (structured JSON + markdown)
```

### Current limitations

Only the 30 gold-set feedback records have stored `analysis_results`/`context_matches` in
this database (Phase 5's baseline/context-matching were only ever run against the gold
set), so most periods will show most feedback as "not yet classified/retrieval-processed" in
the Data Limitations section rather than contributing to counts - this is a demo-dataset
gap, not a report-logic bug. Also: the evidence pack's `MAX_THEMES=8` cap silently drops
themes past the top 8 in a busy period; "new" themes currently appear in both "Top Pain
Points" and "Growing Themes." Full list: `backend/results/reports/report_error_analysis.md`.

### Deferred (Phase 7+)

Frontend, Celery/Redis, authentication, and scheduled/automatic report generation - see
`docs/project_plan.md`.
