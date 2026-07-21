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

Full setup/run commands: `backend/README.md`.
