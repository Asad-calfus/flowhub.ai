# 0008 — Frontend/Backend Repo Split

**Date**: 2026-07-21
**Status**: Complete

## What changed

Moved `data/`, `results/`, `scripts/`, `src/`, `tests/`, `requirements.txt`, `pytest.ini`,
`.env*` into `backend/`. Added `frontend/` with a placeholder README only (Phase 7, not
started). `README.md`, `PROJECT_CONTEXT.md`, `CHANGELOG.md`, `docs/` stay at root - they
describe the whole project, not just the backend.

## Why

User wants the repo structured as frontend/backend from the start, with all backend files
grouped under `backend/`.

## Files changed

```
backend/{data,results,scripts,src,tests,requirements.txt,pytest.ini,.env,.env.example}  (moved)
backend/README.md      (new - backend-specific run commands, split out of root README)
frontend/README.md     (new - placeholder)
README.md              (rewritten - short overview + pointers)
PROJECT_CONTEXT.md, docs/project_plan.md   (path references prefixed with backend/)
.gitignore             (backend/results/cache paths)
```

## How to verify

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python3 -m pytest -q                        # 65/65 passing
python3 scripts/data/validate_dataset.py    # 23/23 passing
```

## Notable decisions

- No code changes needed beyond the moves: every script computes its root via a fixed number
  of `dirname()` calls from `__file__`, and since `data/`/`results/`/`src/` all moved one
  level deeper together (into `backend/`), that arithmetic still resolves correctly - it now
  lands on `backend/` instead of the repo root, which is exactly right.
- Old root-level `.venv` was orphaned by this move (venvs can't be relocated - absolute paths
  break) and a fresh one was created under `backend/.venv`. The stale root `.venv/` is
  gitignored either way; delete it manually if you want it gone (rm -rf needs your
  confirmation, not run here).
- Historical changelog entries (0001-0007) were left describing the pre-split paths as they
  existed at the time.

## Follow-ups deferred

Frontend implementation itself (Phase 7, unchanged position in the roadmap).
