# 0024 — Frontend UI for corrections/churn/copilot + PDF chart visualizations

**Date**: 2026-07-22
**Status**: Complete

## What changed

Backend-only features from 0020-0022 now have UI, and the PDF export (0023) includes charts,
not just tables. Also root-caused and fixed why none of it was visible: the Docker backend's
`uvicorn --reload` had stopped picking up file changes on the bind mount (WatchFiles never
fired a reload after the initial startup 18+ hours ago) - every route added this session
(corrections, churn, copilot, PDF, share link) was 404/stale until `docker compose restart
backend` picked up the current code in one shot. No code change fixes this by itself; noting
it here since it'll recur if the dev container sits long enough without a restart.

### Human-in-the-loop corrections UI
- **`components/CorrectionEditor.tsx`** (new): inline per-field editor on the feedback detail
  page (`app/feedback/[id]/page.tsx`) - pencil icon next to each of the 5 classification
  fields opens a `<select>` of that field's allowed values, saves via `PATCH /analysis/{id}/
  classification`, then refetches the page data. Correction history (original → corrected,
  by whom, when) renders below from `GET /analysis/{id}/corrections`.
- `lib/api.ts`/`lib/types.ts`: `correctClassification`, `listCorrections`, `getCorrectionStats`,
  `CorrectionRequest`/`CorrectionOut`/`CorrectionStatsOut`/`CorrectableField`.

### Churn risk UI
- **`app/churn/page.tsx`** (new): metric cards (customers tracked / high / medium risk), a
  top-10 at-risk bar chart (`DistributionBarChart`, reused as-is), and a full sortable-by-
  risk table (tier, score, level badge, feedback/negative/high-urgency counts, last sentiment).
- **`components/Badges.tsx`**: new `RiskBadge` (Low/Medium/High, same style convention as
  `SentimentBadge`/`UrgencyBadge`).
- `lib/api.ts`/`lib/types.ts`: `listAtRiskCustomers`, `getCustomerRisk`, `CustomerRiskOut`.

### AI Copilot UI
- **`app/copilot/page.tsx`** (new): question input + `ProcessingModeToggle` (local dry-run vs.
  live LLM, reusing the same component as the report generation form), running Q&A history
  with the answer, model name, and linked source feedback (id, preview, sentiment, similarity)
  per turn.
- `lib/api.ts`/`lib/types.ts`: `askCopilot`, `CopilotAskRequest`/`CopilotAnswerOut`/`CopilotSource`.

### Nav
- **`components/Sidebar.tsx`**: added "Churn Risk" and "AI Copilot" entries.

### PDF chart visualizations
- **`src/reports/pdf_renderer.py`**: added `_sentiment_pie_chart()` and
  `_distribution_bar_chart()` using `reportlab.graphics.charts` (Pie / VerticalBarChart) - no
  new dependency, reportlab already ships these. Same palette as the web view
  (`_SENTIMENT_COLORS` mirrors `frontend/components/charts/SentimentChart.tsx`,
  `_BAR_COLOR` matches the module-distribution bar on the report detail page). Inserted: a
  sentiment pie + feedback-by-module bar chart in section 2, and a %-negative-by-module bar
  chart in section 5 ("Most Negative Product Modules").

## Why

The four features existed at the API level only; the user couldn't see them because (a) no
frontend called them yet, and (b) the running dev backend was serving stale code from before
any of this session's work, so even direct API calls were failing/404ing. Also asked for the
PDF export to include visualizations, not just a metrics table.

## Verification

- `docker compose restart backend` + direct `curl` against `/churn/customers`,
  `/copilot/ask`, `PATCH /analysis/{id}/classification`, `/reports/{id}/pdf` - all 200,
  PDF downloaded is a valid 10-page document with chart content.
- `.venv/bin/python -m pytest tests/reports/test_pdf_renderer.py -q` → 4/4 passed (chart
  builders return a `Drawing` for non-empty data, `None` for empty/all-zero data).
- `.venv/bin/python -m pytest tests/ -q` (excluding the two pre-existing unrelated failures)
  → 236 passed.
- `npx tsc --noEmit` and `npx vitest run` in `frontend/` → clean, 28/28 passed.
- Confirmed the frontend dev server (running on the host, not Docker) picked up all new
  pages live via Next.js Fast Refresh - `/churn`, `/copilot`, `/feedback/FB-0001` all return
  200 without a restart.

## Notable decisions

- Charts in the PDF use reportlab's own vector chart support (`reportlab.graphics.charts`),
  not matplotlib-to-PNG - no new dependency, and vector output scales cleanly in a PDF
  viewer instead of a fixed-resolution raster image.
- Churn and Copilot got new top-level pages rather than being folded into the dashboard -
  each has its own distinct interaction (a ranked table, a live Q&A history) that doesn't fit
  a metric-tile layout.
- No customer detail page - `customer_id` isn't filterable on the feedback list endpoint yet,
  so the churn table doesn't (yet) link out anywhere; flagged as a real gap if this becomes a
  primary workflow, not silently worked around.
