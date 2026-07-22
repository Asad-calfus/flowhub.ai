# FlowHub AI Customer Feedback Intelligence Platform

Starting a new phase or a fresh session? Read `PROJECT_CONTEXT.md` first, then
`docs/project_plan.md` for the roadmap.

## Repo layout

```text
backend/     # Python AI/data pipeline + FastAPI/Postgres layer - see backend/README.md
frontend/    # Next.js dashboard (Phase 7) - see frontend/README.md
docs/        # project-wide docs: dataset design, roadmap, changelog
```

## Quick start

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest -q
```

## Backend API (Phase 5)

```bash
docker compose up -d db          # Postgres 16 + pgvector, http://localhost:5433
cd backend
alembic upgrade head
python3 scripts/import_data.py   # backfill the existing dataset/results (safe to re-run)
uvicorn app.main:app --reload --port 8001
```

Full setup/run commands, API endpoints, and schema: `backend/README.md`.

## Weekly insight reports (Phase 6)

```bash
cd backend
python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10
python3 scripts/pipeline/evaluate_weekly_report.py
```

Deterministic by default (no LLM, no cost); optional LLM narrative mode is dry-run unless
`--mode live` is passed explicitly. Details: `backend/README.md`'s "Phase 6" section.

## Dashboard (Phase 7)

```bash
docker compose up -d db backend   # backend on http://localhost:8001
cd frontend
cp .env.example .env.local
npm install
npm run dev                       # http://localhost:3000
```

Or the whole stack: `docker compose up -d` (adds a `frontend` service on port 3000).
Details, pages, and tests: `frontend/README.md`.
cd frontend && npm install && cp .env.example .env.local && npm run dev   # :3000
