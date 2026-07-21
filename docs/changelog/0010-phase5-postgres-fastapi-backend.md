# 0010 — Phase 5: PostgreSQL and FastAPI Backend

**Date**: 2026-07-21
**Status**: Complete

## What changed

Added `backend/app/` (FastAPI application) and `backend/alembic/` (migrations), backed by
PostgreSQL + pgvector, exposing the existing Phase 1-4 pipeline (`backend/src/`) over HTTP.
No classification, retrieval, or clustering logic was reimplemented - the API layer calls
into `src/classification/`, `src/retrieval/`, and `src/themes/` directly.

- **Structure**: `app/{api,core,models,schemas,repositories,services}` - routes call
  services, services call repositories (DB) and `src/` (pipeline logic); routes never touch
  SQLAlchemy directly. `app/core/config.py` (env-driven `Settings`), `app/core/database.py`
  (engine/session/`Base`), `app/core/exceptions.py` (domain exceptions mapped to HTTP status
  codes by handlers in `app/main.py`).
- **Tables** (`app/models/`, one Alembic migration `b2dff81a8a6d_initial_schema.py`):
  `feedback` (raw only, no generated fields - reprocessable), `analysis_results` (one row per
  classification run, not overwritten - full history), `embeddings` (pgvector `vector(384)`,
  one current row per feedback), `context_records` (known bugs/feature requests/releases/
  product modules unified, `context_type` discriminator, optional `vector`), `context_matches`
  (one row per candidate pairing, `match_status` matched/candidate), `themes`, `theme_members`
  (`membership_score` doubles as the representative-selection signal - see Notable decisions).
- **Import** (`app/services/import_service.py` + `scripts/import_data.py`): backfills all 150
  feedback records, 8 modules, 15 bugs, 12 feature requests, 6 releases, cached Phase 3
  embeddings, baseline classification predictions, gold-set context matches, and Phase 4 theme
  assignments - straight from the existing CSV/JSON/npy result files, no recomputation, no LLM
  calls. Every insert is existence-checked (never a bare `INSERT`), so re-running only
  produces skips.
- **APIs** (`/api/v1`, routes in `app/api/routes/`): feedback CRUD + CSV import + filtered/
  paginated list; analysis (single, batch, get-latest) reusing `classify_baseline`/
  `FewShotClassifier` unchanged; retrieval (similar-feedback, context-matches) via pgvector
  `cosine_distance`/`cosine_top_k` against embeddings stored in Postgres instead of the
  standalone pipeline's local `.npy` cache; themes (list, detail, member feedback).
  `GET /health` (root) and `GET /api/v1/status` (DB round-trip check).
- **Cost safety carried over unchanged** ([[feedback_openai_cost_safety]]): `POST
  /api/v1/analysis/{id}` defaults to `method=baseline`; `method=llm` defaults to
  `live=false` (dry-run stub); `live=true` raises `503` immediately if no provider API key is
  configured - no path in the API can trigger a real LLM call without an explicit `live=true`
  in the request body.
- **Docker Compose** (`../docker-compose.yml`, repo root): `db` (pgvector/pgvector:pg16,
  `CREATE EXTENSION vector` via `backend/scripts/db/init_pgvector.sql` on first boot) and
  `backend` (runs `alembic upgrade head` then `uvicorn --reload`). Host ports `5433`/`8001` -
  `5432`/`8000` were already taken by another project's containers on this machine.
- **Tests** (`backend/tests/api/`, 33 new): health, feedback CRUD + validation, CSV import +
  duplicate prevention + invalid-format rejection, pagination/filtering, analysis storage +
  batch + live-without-key + 404s, similar-feedback + context-matches, theme endpoints,
  batch-analysis rollback isolation. Isolated `flowhub_test` Postgres database
  (`tests/api/conftest.py`), tables created/dropped per session, truncated per test.

## Why

Phase 5 of `docs/project_plan.md` - persist feedback/results in Postgres and expose the
already-proven AI core over HTTP, so a future frontend (Phase 7) has something to call.

## Files changed

```
backend/app/                                             (new - FastAPI app)
backend/alembic/, alembic.ini                            (new - migrations)
backend/scripts/import_data.py, scripts/db/init_pgvector.sql  (new)
backend/tests/api/                                       (new, 33 tests)
backend/Dockerfile                                        (new)
docker-compose.yml                                         (new, repo root)
backend/requirements.txt   (fastapi, sqlalchemy, alembic, psycopg, pgvector, uvicorn,
                             pydantic-settings, python-multipart, httpx)
backend/.env, .env.example  (DATABASE_URL, CORS_ORIGINS)
README.md, PROJECT_CONTEXT.md, docs/project_plan.md, backend/README.md, CHANGELOG.md
```

## Results

- **Import**: 150/150 feedback, 41/41 context records (8 modules + 15 bugs + 12 features + 6
  releases), 150/150 embeddings, 30/30 baseline analysis results (baseline was only ever run
  on the gold set - see Notable decisions), 270 context-match rows across the 30 gold records,
  16/16 themes, 84/84 theme members. Re-running reports 0 imported / everything skipped.
- **Tests**: 131/131 passing (98 pre-existing Phase 1-4 tests, unchanged, + 33 new).
- **Migration**: one revision (`b2dff81a8a6d`), applies cleanly to a fresh `pgvector/pgvector:pg16`
  database.

## How to verify

```bash
cd backend
docker compose -f ../docker-compose.yml up -d db      # or run your own Postgres 16 + pgvector
alembic upgrade head
python3 scripts/import_data.py
python3 -m pytest -q                                   # 131 passed
uvicorn app.main:app --reload --port 8001
curl localhost:8001/health
curl localhost:8001/api/v1/status
curl localhost:8001/api/v1/feedback?page_size=5
```

## Notable decisions

- **Baseline predictions imported, LLM predictions not.** `results/llm_predictions.csv` is a
  dry-run stub (`"DRY_RUN stub - no API call made"` - see `docs/changelog/0003-*.md`), and
  `results/baseline_predictions.csv` only covers the 30 gold records (that's what
  `run_baseline.py` was ever scoped to - see `backend/src/data_loader.py::load_gold_records`).
  Importing the dry-run stub as if it were a real analysis result would misrepresent it, so
  only the genuine baseline predictions were imported; the other 120 feedback records stay
  `processing_status="pending"` until analyzed via the API.
- **`ThemeMember.membership_score` reused as the representative signal, not stored twice.**
  Rather than adding a separate `representative_feedback_ids` column to `themes` (redundant
  with `theme_members`), representative-selection during import assigns members that appear
  in `themes.csv`'s `representative_feedback_ids` a descending score (1.00, 0.99, 0.98) and
  leaves everyone else `NULL`. `GET /api/v1/themes/{id}` picks the top-3 by score - same
  members Phase 4's centroid-similarity ranking chose, at the cost of not persisting the
  *exact* centroid-similarity float (not present in `themes.csv` to begin with).
- **Feedback is embedded at creation time, not lazily on first retrieval.** An early version
  only embedded a feedback record when *its own* similar-feedback/context-match endpoint was
  hit - which meant a freshly created record had no embedding for anything *else* to match
  against. `feedback_service.create_feedback` and CSV import now call
  `embedding_service.ensure_embedding` immediately (same `src/retrieval/embedder.py` and
  `text_builder.py` as the standalone pipeline), so nearest-neighbor search always sees every
  record that exists. The one-time `import_data.py` backfill still uses the Phase 3 `.npy`
  cache instead, so it doesn't re-embed 150 records through the model on every run.
  Caught by `tests/api/test_retrieval.py::test_similar_feedback_returns_other_record` before
  this was fixed.
- **Batch analysis uses a savepoint (`db.begin_nested()`) per item**, not a bare try/except.
  A plain except around a failed classification would still have already-`flush()`ed changes
  from a *later* item's exception unwind the *earlier* items' uncommitted work at the outer
  transaction level (Postgres aborts the whole transaction on error otherwise). The savepoint
  scopes the rollback to just the failing item, matching the "one failure doesn't lose the
  rest of the batch" requirement.
- **Similarity search runs on pgvector's `cosine_distance` operator** (an index-ready
  Postgres-native comparison) rather than loading every embedding into Python and calling the
  Phase 3 `cosine_top_k` numpy helper - which is still reused as-is for `context_matches`
  (small, in-memory candidate sets: at most 15 bugs/12 features/6 releases) where pulling
  everything into numpy costs nothing.
- Host ports **5433** (Postgres) and **8001** (backend) instead of the defaults - `5432`/
  `8000` were already bound by an unrelated project's containers on this machine.

## Follow-ups deferred

Frontend (Phase 7), weekly LLM summaries (Phase 6), Celery/Redis (Phase 8), authentication
and multi-tenancy (explicitly out of scope for Phase 5 per the spec) - unchanged from
`docs/project_plan.md`. Also deferred within Phase 5 itself: advanced search/full-text
filtering on feedback, async/background batch analysis (currently synchronous, per spec),
API-level rate limiting on live LLM calls, and CI (no `pyproject.toml`/GitHub Actions yet,
same gap noted since `docs/changelog/0004-*.md`).
