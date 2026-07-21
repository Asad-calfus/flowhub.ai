# 0006 — Add Project Plan Roadmap; Move Context Doc to Root

**Date**: 2026-07-21
**Status**: Complete

## What changed

- Rewrote `docs/project_plan.md`: replaced the old pre-build aspirational draft (public +
  synthetic data, 300–500 records, full architecture specced up front) with the actual
  10-phase roadmap, MVP scope, deferred features, stack, leakage rule, testing/git
  conventions, and a "changes made from the original plan" section.
- Moved `docs/project_context.md` → `PROJECT_CONTEXT.md` (root), matching `README.md`/
  `CHANGELOG.md`. Updated the one reference in `README.md`.
- Linked `docs/project_plan.md` from `PROJECT_CONTEXT.md`.

## Why

User wants `docs/project_plan.md` as the standing roadmap for Claude Code and future
contributors, with the original plan's now-outdated dataset assumptions explicitly reconciled
against what was actually built (150 vs. 300–500 records, 30 vs. 50–100 gold, fully synthetic
vs. public+synthetic, FlowHub invented, dataset scripts/context files added earlier).

## Files changed

```
docs/project_plan.md        (rewritten)
PROJECT_CONTEXT.md          (moved from docs/, git history preserved; content updated)
README.md                   (path reference fixed)
CHANGELOG.md                (index entry)
```

## How to verify

Read `docs/project_plan.md` top to bottom; `PROJECT_CONTEXT.md` now links to it.

## Notable decisions

- Old plan content wasn't deleted silently - its dataset-size/source assumptions are now the
  explicit "changes from the original plan" record instead of being left as a stale, ignored
  file.
- No code changed in this entry; test suite untouched.

## Deferred

Phase 3 (embeddings/retrieval) implementation itself is not part of this entry - scope was
limited to the planning doc per this turn's request.
