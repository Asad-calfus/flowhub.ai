# 0023 — Export report as PDF + shareable signed link

**Date**: 2026-07-22
**Status**: Complete (backend + minimal frontend)

## What changed

- **`src/reports/pdf_renderer.py`** (new): renders a `WeeklyReport` to PDF bytes via
  `reportlab`, mirroring `generator.render_markdown`'s 12 sections (executive summary,
  metrics table, pain points, growing themes, negative modules, feature requests, known
  bugs, release issues, enterprise feedback, new/untracked issues, recommended actions, data
  limitations). Built directly from the `WeeklyReport` object, not by converting the
  Markdown - pure rendering, no new numbers/wording. All feedback-derived text is
  XML-escaped before being placed in reportlab `Paragraph` markup (feedback text can contain
  `<`/`>`/`&`, which reportlab's mini-markup would otherwise choke on).
- **`src/reports/signing.py`** (new): HMAC-SHA256 signed, expiring tokens
  (`{report_id}:{expires_at}`, 7-day default TTL) for shareable links - not a general auth
  scheme (this app has none, see `app/core/workspace.py`), just proof a link was minted by
  this server and hasn't expired.
- **`app/core/config.py`** / **`.env.example`**: new `SECRET_KEY` setting (signing key).
- **`app/core/exceptions.py`** / **`app/main.py`**: new `InvalidTokenError` → HTTP 403.
- **`app/services/report_service.py`**: `render_report_pdf()`, `create_share_link()`.
- **`app/api/routes/reports.py`**: `GET /reports/{id}/pdf` (optional `?token=`),
  `POST /reports/{id}/share` (mints a token + full path, 7-day expiry).
- **Frontend**: `lib/api.ts` (`downloadReportPdf`, `createReportShareLink`),
  `app/reports/[id]/page.tsx` - "Download PDF" (blob → browser download) and "Share link"
  (mints a token, copies the full URL to the clipboard) buttons on the report detail page.

## Why

Item 4 of the rereflect-inspired feature set: exportable PDF reports and shareable signed
links, matching rereflect's "Exportable PDF reports and shareable signed links" feature.

## Verification

- `.venv/bin/pip install reportlab` (host venv) + `docker compose exec backend pip install
  reportlab` (running container, for live testing) - also added to `requirements.txt`.
- `.venv/bin/python -m pytest tests/reports/test_signing.py tests/api/test_reports.py -q` →
  19/20 passed, 1 pre-existing unrelated failure (same real-API-key environment issue noted
  in [[0019]](0019-all-time-report-mode.md)). New tests: PDF download returns a real `%PDF`
  body, missing report 404s, share-link token grants access, invalid token → 403,
  token-for-a-different-report → 403 (5 API tests); token sign/verify/expiry/tamper/garbage
  (5 unit tests in `tests/reports/test_signing.py`).
- `.venv/bin/python -m pytest tests/ -q` (excluding the two pre-existing unrelated failures)
  → 232 passed.
- `npx tsc --noEmit` and `npx vitest run` in `frontend/` → clean, 28/28 passed.
- Manual: hit `POST /reports/{id}/share` then `GET /reports/{id}/pdf?token=...` against the
  running dev container - real PDF bytes returned.

## Notable decisions

- Chose `reportlab` over `weasyprint`/`pdfkit` - pure-Python-ish wheels, no system
  dependency (no Cairo/Pango/wkhtmltopdf to install in the Docker image), and gives direct
  control over layout via flowables rather than round-tripping through HTML.
- Token carries only `report_id` + expiry, not a general capability token - `verify_signed_
  token` takes the expected `report_id` explicitly and rejects a token minted for a
  different report, so one leaked link can't be reused to access other reports.
- `GET /reports/{id}/pdf` works both with and without a token: omit it for normal in-app
  access (this app has no auth to enforce either way - see `app/core/workspace.py`), supply
  a valid one to access the same PDF from outside the app. An invalid/expired/mismatched
  token is always rejected (403), even though an *absent* token is allowed through.
