# 0013 — Frontend: CSV Feedback Import

**Date**: 2026-07-21
**Status**: Complete

## What changed

Added a CSV upload control to the Feedback Inbox page (`frontend/components/
FeedbackCsvImport.tsx`), wired to the existing `POST /api/v1/feedback/import` endpoint - no
new backend logic, no client-side CSV parsing or validation duplicating what the backend
already does.

- **API client** (`lib/api.ts`): added `api.importFeedbackCsv(file)`, and split `request()`
  into a shared `toResult()` response handler plus a new `requestForm()` path for
  `multipart/form-data` bodies - the existing `request()` always forced a JSON
  `Content-Type` header, which would have broken the browser's multipart boundary.
- **Types** (`lib/types.ts`): added `ImportSummary`, mirroring
  `app/schemas/feedback.py::ImportSummary`.
- **Component** (`components/FeedbackCsvImport.tsx`): file picker restricted to `.csv`,
  a 10MB client-side size guard (rejected before any network call), upload state, and a
  result panel showing imported/skipped counts and any per-row errors straight from the
  backend's `ImportSummary` - not recalculated. `app/feedback/page.tsx` refreshes the list
  (`retry()`) after a successful import.
- **Tests** (`tests/FeedbackCsvImport.test.tsx`, 4 new): non-CSV file rejected without a
  network call; successful upload sends a real `FormData` (not JSON, no forced
  `Content-Type`) and renders the returned summary; per-row `errors` array is surfaced;
  backend rejection (400) shows the backend's `detail` message.

## Why

The task only exposed CSV import via `scripts/import_data.py` (that script backfills the
whole Phase 1-4 dataset from local files) and the raw API - there was no way for someone
using the dashboard to add new feedback without a terminal. This closes that gap using the
endpoint that already existed for exactly this purpose.

## Files changed

```
frontend/lib/api.ts        (requestForm/toResult split, importFeedbackCsv)
frontend/lib/types.ts       (ImportSummary)
frontend/components/FeedbackCsvImport.tsx   (new)
frontend/app/feedback/page.tsx              (mounts the import control, refreshes on success)
frontend/tests/FeedbackCsvImport.test.tsx   (new, 4 tests)
frontend/README.md
CHANGELOG.md
```

## Results

- **Tests**: 25/25 passing (21 previous + 4 new).
- **Type-check**: clean.
- **Manual verification against the real running stack**: uploaded a 2-row sample CSV via
  `curl -F file=@sample.csv` directly to `POST /api/v1/feedback/import` - `200`,
  `feedback_imported: 2, feedback_skipped: 0, errors: []`; confirmed `GET /feedback`'s
  `total` moved from 150 to 152; confirmed the Feedback Inbox page still renders after the
  change (hot-reloaded, no console/server errors).

## How to verify

```bash
cd frontend && npm test              # 25 passed
npx tsc --noEmit                     # clean

# with the backend running:
curl -X POST http://localhost:8001/api/v1/feedback/import -F "file=@sample.csv"
```
Or use the UI: Feedback Inbox → "Choose CSV file".

## Notable decisions

- **No client-side CSV parsing.** The file is sent as-is to the backend, which already owns
  validation (required columns, UTF-8 decoding, dedup-by-`feedback_id`, per-row error
  collection) - parsing it twice would risk the frontend accepting something the backend
  rejects, or vice versa.
- **10MB client-side size cap is a UX guard, not a security boundary.** It exists only to
  fail fast on an obviously-wrong file pick before spending a network round-trip; the
  backend enforces its own limits independently.
- **List doesn't jump to the newly imported rows.** `GET /feedback` orders by ascending
  `Feedback.id`, so new rows land on the *last* page, not page 1. Rather than guess a
  destination page, the import panel just reports the summary and calls `retry()` to
  refresh counts on whatever page the user is currently viewing.

## Follow-ups / deferred

Same v2 boundary as Phase 7 (`docs/changelog/0012-*.md`) - nothing here changes that. A
"jump to newest" convenience (e.g. sort-by-newest toggle) would be a small, separable
follow-up if needed later.
