# 0014 — Frontend: Home page + Chattermill/Thematic-inspired redesign

**Date**: 2026-07-21
**Status**: Complete

## What changed

Full visual/IA redesign of `frontend/` — no backend changes, no API contract changes, same
Next.js/TypeScript/Tailwind/Recharts stack. One new dependency: `lucide-react` (icons).

- **New information architecture**: `/` is now a proper Home/landing page (hero, KPI ribbon,
  "how it works" pipeline strip, latest-report teaser, quick-nav cards) instead of dropping
  straight into analytics. The former Overview page moved to `app/dashboard/page.tsx`
  unchanged in logic. Sidebar nav updated to Home / Dashboard / Feedback Inbox / Themes /
  Weekly Reports / Evaluation, each with an icon and active-state indicator.
- **Design tokens** (`tailwind.config.ts`, `app/globals.css`): replaced the generic blue
  `brand` scale with an indigo scale + a violet `accent`, added `shadow-card`/
  `shadow-card-hover`, `.btn-primary`/`.btn-secondary`/`.btn-danger` utility classes (buttons
  were previously ad hoc inline Tailwind strings), expanded `.card` (rounded-xl, soft
  shadow) and added `.card-interactive` for clickable cards. Added Inter via `next/font`.
- **Shared shell**: `Sidebar.tsx` rewritten with icons and a responsive off-canvas drawer on
  small screens (was desktop-only); `PageHeader.tsx` restyled into a sticky top bar, same
  `title`/`description`/`action` prop contract.
- **Every page restyled** (Feedback Inbox/Detail, Themes list/detail, Reports list/detail,
  Evaluation) — icons, consistent spacing/typography, `max-w` content containers, trend
  badges with icons (Sparkles/TrendingUp/TrendingDown/Minus), `ThemeCard` gained a relative
  feedback-volume bar. No page's data-fetching logic or prop contracts changed.
- **Sentiment chart palette fixed**: the 4-color sentiment pie
  (`components/charts/SentimentChart.tsx`) failed the dataviz skill's categorical
  color-blindness validator (`scripts/validate_palette.js`) - `#fab219` failed the lightness
  band, `#898781` read as too gray to serve as a category. Replaced with a validated
  4-hue set (`#008300` / `#2a78d6` / `#e34948` / `#4a3aa7`) that passes CVD separation,
  normal-vision separation, and contrast in light mode. `SentimentBadge`'s standalone status
  pills (used one-at-a-time with their own label, not a shared legend) were left as
  emerald/rose/amber/slate - that's a WCAG-contrast concern, not a categorical-adjacency one.

## Why

The dashboard was functionally complete (Phases 1-7) but looked like a bare admin skin -
generic blue accent, text-only sidebar links, no landing page. The ask was to restructure
the UI flow (add a real Home page) and raise the visual bar to something inspired by
Chattermill/Thematic (customer-feedback-analytics products), without touching the backend
or the AI pipeline underneath it.

## Files changed

```
frontend/tailwind.config.ts          (brand/accent tokens, shadow-card, Inter font hookup)
frontend/app/globals.css             (.card, .btn-*, .section-label, table-base restyle)
frontend/app/layout.tsx              (Inter font)
frontend/app/page.tsx                (new Home page)
frontend/app/dashboard/page.tsx      (new - former Overview content, restyled)
frontend/components/Sidebar.tsx      (icons, responsive drawer)
frontend/components/PageHeader.tsx   (sticky top bar restyle)
frontend/components/MetricCard.tsx   (optional icon/tone props, backward compatible)
frontend/components/Badges.tsx       (icons on TrendBadge, rose replaces red)
frontend/components/States.tsx       (icons on Error/EmptyState)
frontend/components/HealthBadge.tsx  (pill restyle, pulse animation)
frontend/components/ThemeCard.tsx    (relative feedback-volume bar)
frontend/components/FeedbackFilters.tsx, FeedbackCsvImport.tsx, FeedbackTable.tsx,
  Pagination.tsx, ReportGenerationForm.tsx, EvidenceLinks.tsx  (visual polish only)
frontend/components/charts/SentimentChart.tsx  (validated categorical palette)
frontend/app/feedback/page.tsx, feedback/[id]/page.tsx
frontend/app/themes/page.tsx, themes/[id]/page.tsx
frontend/app/reports/page.tsx, reports/[id]/page.tsx
frontend/app/evaluation/page.tsx
frontend/package.json                (+lucide-react)
CHANGELOG.md
```

## Results

- **Tests**: 25/25 passing, unchanged (existing tests assert behavior/text/roles, not
  styling, so none needed rewriting).
- **Type-check**: clean (`npx tsc --noEmit`).
- **Manual verification against the running stack**: every route (`/`, `/dashboard`,
  `/feedback`, `/themes`, `/reports`, `/evaluation`) and each dynamic detail route
  (`/feedback/FB-0001`, `/themes/THM-001`, `/reports/RPT-0005`) returns `200` with the
  backend running; no console/build errors.
- **Palette**: sentiment categorical set passes `validate_palette.js --mode light` (CVD
  separation, normal-vision separation, lightness band, contrast all PASS).

## How to verify

```bash
cd frontend && npm test              # 25 passed
npx tsc --noEmit                     # clean
npm run dev                          # click through Home → Dashboard → Feedback →
                                      # Themes → Reports → Evaluation
```

## Notable decisions

- **Light-only for now.** Dark mode was scoped out explicitly (confirmed with the user) -
  tokens are already indirected through Tailwind config keys, so adding a dark variant later
  is additive, not a rework.
- **No fabricated metrics on the Home page.** Every number (total feedback, theme count,
  latest report's new-issue count/confidence, top theme/issue teaser) comes from an existing
  endpoint the Dashboard already called - consistent with the "every number traces to stored
  data, never invented" principle used throughout the backend.
- **`lucide-react` is the only new dependency.** Everything else stays on existing package
  versions, per the "keep core tech the same" constraint.

## Follow-ups / deferred

Dark mode (explicitly deferred, see above). A generated frontend/backend type client is
still out of scope (unchanged from Phase 7 - `lib/types.ts` stays hand-kept in sync).
