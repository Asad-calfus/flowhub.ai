# Frontend — Phase 7 dashboard

Next.js (App Router) + TypeScript + Tailwind + Recharts dashboard over the Phase 5/6
FastAPI backend. No business logic here - every number comes from an existing API
response or a pre-computed evaluation result file; nothing is recalculated client-side.

## Run locally

```bash
cd frontend
cp .env.example .env.local   # adjust NEXT_PUBLIC_API_BASE_URL if the backend isn't on :8001
npm install
npm run dev                  # http://localhost:3000
```

Requires the backend running (`docker compose up -d db backend` from the repo root, or
`uvicorn app.main:app --port 8001` locally) and `CORS_ORIGINS` on the backend including
`http://localhost:3000` (the default in `backend/.env.example`).

## Tests

```bash
npm test
```

Vitest + React Testing Library. Covers: API-client error handling, feedback table
rendering, filter query-param construction, loading/empty/error states, report-generation
form validation, and dry-run result labeling.

## Pages

| Route | Purpose |
|---|---|
| `/` | Overview - total feedback, and (from the most recent weekly report) sentiment/type/module distributions, top/growing themes, known-bug and feature-request matches, new untracked issues |
| `/feedback` | Paginated, filterable feedback inbox (source, sentiment, category, module, tier) + CSV upload (`POST /feedback/import`) |
| `/feedback/[id]` | Original data, AI analysis, retrieved similar feedback/context matches, theme assignment - kept visually separate |
| `/themes` , `/themes/[id]` | Theme cards and detail (keywords, trend, sentiment, representative + member feedback) |
| `/reports` , `/reports/[id]` | Report list, a deterministic-report generation form, and full report detail (structured view or rendered Markdown) |
| `/evaluation` | Classification/retrieval/theme/report evaluation metrics, read from `backend/results/*.json` via a server-side route - dry-run LLM results are labeled, never presented as real model performance |

## Why the Overview page uses the latest weekly report for distributions

There is no bulk analytics endpoint aggregating classification results across *all*
feedback - `GET /feedback` returns raw feedback only (no sentiment/category/module), and
those live on `AnalysisResult`, fetched one feedback record at a time. The one place the
backend *does* compute period-wide sentiment/type/module distributions is
`SummaryMetrics` inside a generated `WeeklyReport`. Rather than duplicate that aggregation
client-side (or worse, invent it from a partial page of records), the Overview page reads
it from the most recently generated report and labels the period it covers. If no report
exists yet, it says so and links to the Reports page instead of showing zeros.

## CSV import

The Feedback Inbox page has an upload control (`components/FeedbackCsvImport.tsx`) over the
existing `POST /api/v1/feedback/import` endpoint - no new backend logic, no client-side CSV
parsing. Only `feedback_text` is required; optional columns: `feedback_id`, `source`,
`created_at`, `customer_id`, `customer_tier`, `product_version`, `rating`, `language`. Rows
whose `feedback_id` already exists are skipped, not duplicated, so re-uploading the same file
is safe. The response summary (imported/skipped counts, per-row errors) is shown as-is - the
frontend never recalculates or reformats those numbers.

## Known limitation: theme assignment on the feedback detail page

There's no `GET /feedback/{id}/theme` endpoint. The detail page finds it by fetching all
themes and checking each one's member list client-side (`app/feedback/[id]/page.tsx`) -
fine at the current ~150-record/16-theme scale, but it's an O(themes) client-side join, not
a real lookup endpoint. Worth a dedicated backend endpoint if the dataset grows.
