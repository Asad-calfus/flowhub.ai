# Project Context — FlowHub AI Customer Feedback Intelligence Platform

**Purpose of this doc**: a single entry point summarizing everything built so far, so the
next phase can start without re-reading the whole repo. It's a snapshot/index, not the
authoritative source for any topic - follow the links for detail, and treat this doc as
possibly stale on anything it doesn't link to a source file for.

**Last updated**: 2026-07-21, after `docs/changelog/0010`.

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

**Current results** (baseline; LLM numbers are identical right now because no live API key
has been used yet - `llm_predictions.csv` reflects the dry-run stub, not a real model):

| field | accuracy |
|---|---|
| feedback_type | 0.40 |
| category | 0.43 |
| product_module | 0.83 |
| sentiment | 0.27 |
| urgency | 0.43 |

Full breakdown and known failure modes: `backend/results/error_analysis.md`. Sentiment is the
weakest field - VADER under-reacts to long, matter-of-fact negative support tickets. A real
LLM run is expected to improve most fields meaningfully; that hasn't been measured yet.

**Cost-safe real-key usage** (`docs/changelog/0003-*.md`): `backend/scripts/pipeline/run_llm.py`
always dry-runs unless `--live` is passed explicitly; `--live` prints a cost estimate
(`backend/src/classification/pricing.py`) and asks for confirmation. Recommended model: `gpt-4o-mini`.

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

## Explicitly NOT built yet

Weekly summary generation, frontend, Celery/Redis, authentication/multi-tenancy, CI/CD, and
packaging (`pyproject.toml`). Deferred by explicit decision at each phase, not forgotten -
see `docs/project_plan.md` and each changelog entry's "Follow-ups deferred". (The API layer
and database were in this list through Phase 4; both now exist as of Phase 5.)

## Quick orientation for a fresh session

1. Read this doc, then `README.md` for exact run commands.
2. If touching the dataset: `docs/dataset/data_dictionary.md` + `docs/dataset/taxonomy.md`
   first.
3. If touching the classifier: `backend/src/classification/schemas.py` first (the leakage
   contract), then `backend/results/error_analysis.md` for known weak points.
4. If touching the API/database: `backend/app/core/database.py` + `backend/app/models/` for
   the schema, `backend/README.md`'s "Phase 5" section for endpoints/commands.
5. Run `python3 -m pytest -q` before and after any change (131 tests at last count - needs
   `docker compose up -d db` and a `flowhub_test` database, see `backend/README.md`).
6. Add a `docs/changelog/000N-*.md` entry + `CHANGELOG.md` line, then commit, before
   considering a change done.
