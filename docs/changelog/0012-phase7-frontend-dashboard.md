# 0012 — Phase 7: Frontend Dashboard

**Date**: 2026-07-21
**Status**: Complete

## What changed

Added `frontend/` - a Next.js (App Router) + TypeScript + Tailwind + Recharts dashboard
over the existing Phase 5/6 FastAPI API. No backend logic changed; no analytics
recalculated client-side.

- **API client & types** (`lib/api.ts`, `lib/types.ts`): a single `request()` wrapper
  (base URL from `NEXT_PUBLIC_API_BASE_URL`, JSON parsing, a typed `ApiError` carrying the
  backend's `detail` message and HTTP status) and hand-kept-in-sync TypeScript mirrors of
  every `app/schemas/*.py` model and the `Literal` vocabularies they wrap
  (`src/classification/schemas.py`, `src/retrieval/schemas.py`, `src/themes/schemas.py`,
  `src/reports/schemas.py`). `lib/useApi.ts` is a small hook giving every page
  loading/error/retry state without a data-fetching library.
- **Shared UI** (`components/`): `Sidebar`, `PageHeader` + `HealthBadge` (polls `GET
  /health` every 30s), `MetricCard`, `SentimentBadge`/`UrgencyBadge`/`TrendBadge`/
  `ConfidenceBar`/`StatusPill`, `FeedbackTable`, `FeedbackFilters`, `ThemeCard`,
  `EvidenceLinks`, `ReportGenerationForm`, `ErrorState`/`EmptyState`/`Skeleton`,
  `Pagination`. Two chart components (`components/charts/`): a sentiment donut and a
  reusable category/module/theme-volume bar chart, both using the validated categorical/
  status palette from the dataviz skill rather than arbitrary hex values.
- **Pages** (`app/`):
  - `/` Overview - total feedback from `GET /feedback`'s `total`; sentiment/type/module
    distributions and top/growing themes, known-bug/feature-request matches, and new
    untracked issues read from the **most recently generated weekly report**'s
    `SummaryMetrics` (there's no bulk analytics-across-all-feedback endpoint - see Notable
    decisions). Shows an empty-state prompt instead of zeros if no report exists yet.
  - `/feedback`, `/feedback/[id]` - paginated/filterable inbox (source, sentiment,
    category, module, tier - all real backend query params, sentiment/category/module
    filters join to `AnalysisResult` server-side); detail page keeps original data, AI
    analysis, and retrieved evidence (similar feedback, context matches) in visually
    separate sections, plus a theme-assignment lookup (see Notable decisions).
  - `/themes`, `/themes/[id]` - cards/detail with keywords, trend, sentiment
    distribution, representative feedback, paginated member feedback.
  - `/reports`, `/reports/[id]` - report list, a deterministic-only generation form
    (client + server validation: required dates, end ≥ start), and a detail view with a
    structured section-by-section render or the stored Markdown via `react-markdown`
    (never raw HTML injection).
  - `/evaluation` - reads `backend/results/{evaluation_metrics,retrieval/
    retrieval_metrics,themes/theme_metrics,reports/report_evaluation}.json` through a
    server-side route (`app/api/evaluation/route.ts`) - the one page the task spec allows
    to read result files directly. Labels the LLM classification result as a dry-run stub
    (from `llm_run_meta.json`/`run_summary.dry_run`), never presented as real performance.
- **Tests** (`frontend/tests/`, Vitest + React Testing Library, 21 tests): API-client error
  handling (4xx/5xx detail extraction, network failure, success path), feedback table
  rendering (link targets, missing-analysis placeholders), filter query-string
  construction (present vs. omitted params), loading/empty/error state components,
  report-generation form validation (missing dates, end-before-start, valid submit
  payload shape), dry-run result labeling (`StatusPill`, the Evaluation page's dry-run
  badge).
- **Docker Compose**: added a `frontend` service (port 3000, `frontend/Dockerfile`,
  bind-mounts `backend/results` read-only for the evaluation route). No Redis/Celery
  added.

## Why

Phase 7 of `docs/project_plan.md` - a dashboard so a mentor can see the whole system flow
(classification → retrieval → themes → weekly report) without reading API responses by
hand, built strictly on existing endpoints.

## Files changed

```
frontend/                                                    (new)
docker-compose.yml                                           (adds frontend service)
README.md, PROJECT_CONTEXT.md, docs/project_plan.md, CHANGELOG.md
```

## Results

- **Type-check**: `npx tsc --noEmit` - clean.
- **Build**: `npx next build` - compiles successfully, all 10 routes (4 static, 4
  server-rendered dynamic `[id]` routes, 1 API route, 1 not-found) within normal bundle
  sizes (largest page 241 kB first-load JS, `/reports/[id]`, due to `recharts` +
  `react-markdown`).
- **Tests**: 21/21 passing (`npx vitest run`, 6 files).
- **Manual smoke test** against the real stack (`docker compose up -d db`, local
  `uvicorn --port 8001`, `next dev -p 3000`): `/`, `/feedback`, `/feedback/FB-0001`,
  `/themes`, `/themes/THM-001`, `/reports`, `/reports/RPT-0004`, `/evaluation`, and
  `/api/evaluation` all returned `200` with no server-side error markers; spot-checked
  API responses (`GET /api/v1/analysis/FB-0001`, `GET /api/v1/themes`, `GET
  /api/v1/reports`) against the TypeScript types by hand.

## How to verify

```bash
cd frontend
npm install
npm test                 # 21 passed
npx tsc --noEmit         # clean
npx next build           # succeeds

# with the backend running (docker compose up -d db backend, or uvicorn --port 8001):
npm run dev              # http://localhost:3000
```

## Notable decisions

- **Overview distributions come from the latest weekly report, not a new aggregation
  endpoint.** `GET /feedback` returns raw feedback only; category/sentiment/module live
  on `AnalysisResult`, one row per feedback record, with no bulk join-and-aggregate
  endpoint. The only place the backend already computes period-wide distributions is
  `SummaryMetrics` inside a generated `WeeklyReport` (Phase 6). Reusing that - and
  labeling which report/period it's from - avoids either duplicating backend aggregation
  logic in the frontend or reading CSVs directly, both explicitly disallowed by the task
  spec.
- **Feedback Inbox fetches one `GET /analysis/{id}` per visible row.** Same root cause as
  above: there's no `FeedbackOut` + `AnalysisOut` join endpoint. At the default page size
  (20) this is 20 parallel requests per page load - acceptable at this dataset's scale,
  called out as a limitation rather than solved with an unrequested new backend endpoint.
- **Theme assignment on the feedback-detail page is a client-side join across all
  themes.** No `GET /feedback/{id}/theme` endpoint exists. The detail page fetches all
  themes (currently 16) and checks each one's member list for the feedback ID. Explicitly
  not a scalable pattern - documented as a known limitation rather than silently
  papered over.
- **Evaluation page is the only one reading result files directly**, via a server-side
  Next.js route rather than client-side, and only pre-computed JSON metric summaries
  (never the underlying CSVs) - consistent with the task spec's explicit exception for
  this one page and the "use existing APIs, don't read CSVs directly" rule everywhere
  else.
- **`react-markdown` added as the one new runtime dependency beyond the spec'd stack**,
  specifically to satisfy "render stored Markdown safely" without `dangerouslySetInnerHTML`.

## Follow-ups / deferred (Phase 8+)

Celery/Redis, authentication, scheduled/automatic report generation, CI/CD, and a live-LLM
toggle in the main UI were explicitly out of scope for this phase and remain deferred to
Phases 8-10 in `docs/project_plan.md`. Also deferred: a dedicated
`GET /feedback/{id}/theme` (or `GET /analysis` bulk-join) endpoint that would remove the
two client-side-join workarounds noted above; a generated TypeScript client (types are
hand-kept in sync today).
