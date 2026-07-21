# FlowHub AI Customer Feedback Intelligence Platform

Starting a new phase or a fresh session? Read `PROJECT_CONTEXT.md` first, then
`docs/project_plan.md` for the roadmap.

## Repo layout

```text
backend/     # Python AI/data pipeline (dataset, classification, retrieval) - see backend/README.md
frontend/    # Planned (Phase 7, Next.js dashboard) - not started
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
