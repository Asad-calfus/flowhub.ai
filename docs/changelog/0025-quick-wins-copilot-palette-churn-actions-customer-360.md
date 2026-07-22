# 0025 — Cmd+K copilot palette, correction accuracy card, churn actions/review, customer 360

**Date**: 2026-07-22
**Status**: Complete

## What changed

Four rereflect-inspired "quick win" gaps closed, backend where needed + full UI for all of them.

### Cmd+K copilot palette
- **`components/CopilotPalette.tsx`** (new), mounted globally in `app/layout.tsx`: press
  ⌘K/Ctrl+K anywhere to open an overlay, ask a question, get a dry-run answer + linked source
  feedback without leaving the current page. Links to the full `/copilot` page for the
  live-LLM option. The standalone page stays for a fuller Q&A history view.

### Correction accuracy card
- **`app/dashboard/page.tsx`**: 5th metric tile - correction rate (and count) from the
  already-existing `GET /analysis/corrections/stats`, previously computed but never surfaced
  anywhere in the UI.

### Churn suggested action + review flag
- **`src/churn/scoring.py`**: `_suggested_action(risk_level, tier)` - rule-based, no new
  model ("Escalate to account manager immediately" for Enterprise+High, "Reach out
  proactively" for other High, "Monitor and follow up" for Medium, "No action needed" for
  Low). New `reviewed: bool` field on `CustomerRiskScore` (filled in by the service, not the
  scorer, since review state is persisted, not derived).
- **`app/models/churn_review.py`** + **`alembic/versions/c1d8e4f9a2b3_...`** (new table
  `churn_reviews`, one row per customer per workspace, upserted): the score itself stays
  live-computed and never stored; only the human "I've seen this" step is persisted.
- **`app/services/churn_service.py`**, **`app/repositories/churn_review.py`**:
  `mark_customer_reviewed()`. **`app/api/routes/churn.py`**:
  `POST /churn/customers/{id}/review`.
- **`app/churn/page.tsx`**: table gained "Suggested action" and "Reviewed" columns with a
  "Mark reviewed" button; customer_id now links to the new customer page.

### Customer 360 page
- **`app/repositories/feedback.py`** / **`services/feedback_service.py`** /
  **`api/routes/feedback.py`**: new `customer_id` filter on `GET /feedback` (closes the gap
  flagged in [[0021]](0021-churn-risk-scoring.md) - there was no way to list one customer's
  feedback).
- **`app/customers/[id]/page.tsx`** (new): risk score/level/tier/last-sentiment, suggested
  action, mark-reviewed button, and a paginated list of that customer's feedback records
  linking to each one's full detail page.

### Nav / misc
- **`components/Badges.tsx`**: no change needed (`RiskBadge` already existed from 0024).
- `lib/api.ts`/`lib/types.ts`: `markCustomerReviewed`, `suggested_action`/`reviewed` on
  `CustomerRiskOut`, `customer_id` on `FeedbackListFilters`.

## Why

Direct follow-up to the rereflect UI gap analysis: these four were flagged as cheap
(backend-ready or near-ready) and high-value versus the bigger items (Kanban board, new
ingestion sources, settings pages) that were explicitly deferred.

## Verification

- `docker compose exec backend alembic upgrade head` → `churn_reviews` table created.
- `.venv/bin/python -m pytest tests/churn tests/api/test_churn.py tests/api/test_feedback.py -q`
  → 23/23 passed (targeted additions only, not a full re-test of existing scoring/filter
  logic: `test_suggested_action_*`, `test_mark_customer_reviewed`,
  `test_review_unknown_customer_returns_404`, `test_list_feedback_filter_by_customer_id`).
- `.venv/bin/python -m pytest tests/ -q` (excluding the two pre-existing unrelated failures)
  → 241 passed.
- `npx tsc --noEmit` and `npx vitest run` in `frontend/` → clean, 28/28 passed (no new
  frontend tests added - UI-only additions over already-tested API client functions).
- `docker compose restart backend` + direct `curl`: `GET /feedback?customer_id=...`,
  `GET/POST /churn/customers/{id}(/review)` all 200 with `suggested_action`/`reviewed` in the
  response. Frontend dev server (host, Fast Refresh) confirmed serving `/churn`,
  `/customers/{id}`, `/dashboard` at 200 without restart.

## Notable decisions

- `reviewed` lives on a separate `churn_reviews` table, not a column bolted onto `Feedback`/
  `AnalysisResult` - it's a per-customer fact, not per-feedback-record, and the churn score
  itself must stay purely derived (no stored, potentially-stale risk data).
- Kept the standalone `/copilot` page rather than replacing it with the palette - the palette
  is dry-run-only by design (fast, free, no modal-within-modal for the live/local toggle);
  the full page remains where the live-LLM option and turn history live.
