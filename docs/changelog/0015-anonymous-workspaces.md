# 0015 — Anonymous workspaces: upload-your-own-CSV flow

**Date**: 2026-07-22
**Status**: Complete

## What changed

The dashboard no longer always shows the same shared demo dataset. New anonymous
`workspace_id` scoping (no login) separates the existing demo data from anything a
visitor uploads themselves.

**Backend**: `workspace_id` column (default `'demo'`) added to `feedback`, `themes`,
`reports` (migration `f3a9c1b7e2d4`). `app/core/workspace.py`'s `get_workspace_id`
dependency reads an `X-Workspace-Id` header, defaulting to `"demo"` when absent - every
existing test/script keeps working unchanged. Threaded through feedback/theme/report
repositories, services, and routes, plus `src/reports/aggregator.py`. New
`POST /api/v1/themes/recompute` - a live equivalent of
`scripts/pipeline/generate_themes.py`, fed from Postgres embeddings instead of local
cache files, reusing the same clustering/keyword/naming/representative/trend functions
unchanged. Replaces (not merges with) a workspace's existing themes, so it's safe to
call more than once.

**Frontend**: `lib/workspace.ts` generates/stores a workspace id in `localStorage`;
`lib/api.ts` sends it as `X-Workspace-Id` on every call - the only change needed for
every existing page to become workspace-aware. Home (`/`) is now a chooser on first
visit ("View demo" vs "Start your own workspace"); a new `/get-started` page handles
CSV upload → manual "Process my data" button (baseline classification + theme
recompute, both free/local) → redirect to `/dashboard`. A small badge in the sidebar
always shows "Demo data" vs "Your workspace", with a "Switch" action.

## Why

The product is shifting from "one shared demo dashboard" to "bring your own CSV, get
your own dashboard" - explicit user decision. Anonymous workspaces (not real login) and
a manual processing step were chosen deliberately for this iteration; real accounts,
automatic processing, and the eventual demo-dataset story are explicitly deferred.

## Verification

- Backend: 186/186 tests pass (182 existing + 4 new in `tests/api/test_workspaces.py`
  covering feedback/theme isolation and recompute idempotency).
- Frontend: 25/25 tests pass (one pre-existing assertion updated - it checked "no
  headers at all" on the multipart import call; now checks "`Content-Type` still left
  to the browser," since a non-Content-Type header is fine to add).
- Manual end-to-end against the live stack: uploaded 5 rows into a fresh workspace,
  ran batch analysis (exactly 5 processed, not the whole demo backlog), ran
  `/themes/recompute` (1 theme, 4/5 clustered), generated a report - all scoped
  correctly; demo workspace (357 feedback, 16 themes, 5 reports) untouched throughout.

## Notable decision

Mid-implementation, a stale `uvicorn --reload` process (file-watch doesn't reliably
fire over the Colima bind mount) meant one test batch-analysis call ran against
pre-workspace-scoping code and classified ~327 pending demo records instead of the
intended 5. Not destructive - baseline classification is free/deterministic and those
records were unclassified backlog anyway - but worth noting: **restart the backend
container after backend code changes**, don't rely on `--reload` alone in this setup.

## Follow-ups / deferred

Real accounts, cross-device workspace access, automatic (vs. manual) processing,
context-matching relevance for non-FlowHub data, and the real demo-dataset story - all
explicitly out of scope this round, not forgotten.
