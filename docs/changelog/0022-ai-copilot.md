# 0022 — AI Copilot: natural-language Q&A over feedback

**Date**: 2026-07-22
**Status**: Complete (backend only - no frontend UI yet)

## What changed

`POST /copilot/ask` answers a free-text question by embedding it, retrieving the nearest
stored feedback in the workspace, and wording an answer strictly around that retrieved set -
same "retrieval finds the facts, LLM only words the answer" split as the weekly report
generator. Dry-run (deterministic, no API call) by default; `live: true` opts into a real call
and 503s if no provider key is configured, same cost-safety convention as classification/reports.

- **`app/repositories/embedding.py`**: `search_by_vector()` - nearest feedback to an arbitrary
  query vector, joined to `feedback` for workspace scoping (the existing `nearest_neighbors`
  only supported "nearest to an existing feedback_id, excluding itself", not an arbitrary
  question vector).
- **`src/copilot/answerer.py`** (new): `CopilotAnswerer` - dry-run gives a deterministic
  templated summary of the retrieved feedback (count, ids, dominant sentiment); live calls
  Anthropic/OpenAI/Groq with a system prompt that forbids inventing facts outside the supplied
  excerpts. No separate ID-hallucination check needed - the "sources" returned to the caller
  are exactly (and only) what was retrieved, independent of what the model's prose mentions.
- **`app/services/copilot_service.py`**, **`app/schemas/copilot.py`**,
  **`app/api/routes/copilot.py`** (new): wiring, request/response schemas, the endpoint.
- **`app/api/router.py`**: registered.

No migration - reuses the existing `embeddings` table (Phase 3's pgvector setup); no new
storage.

## Why

Item 3 of the rereflect-inspired feature set: a natural-language interface over feedback,
built on retrieval infrastructure that already existed (embeddings, `Embedder`) rather than a
new pipeline.

## Verification

- `.venv/bin/python -m pytest tests/copilot tests/api/test_copilot.py -q` → 8/8 passed
  (deterministic-answer unit tests + API tests: sources populated, empty-workspace message,
  live-without-key 503, question/top_k validation).
- `.venv/bin/python -m pytest tests/ -q` (excluding the two pre-existing unrelated failures) →
  213 passed.

## Notable decisions

- Embeddings for candidate feedback are NOT computed on demand by the copilot - it searches
  whatever's already in the `embeddings` table (populated by the existing similarity-search/
  context-match path). A feedback record with no embedding yet simply won't surface; this
  mirrors the weekly report's existing "unprocessed records are excluded, not silently treated
  as a null result" stance rather than adding a new eager-embedding-on-every-question cost.
- No frontend UI in this pass - same reasoning as corrections/churn: no natural page to hang a
  Cmd+K-style palette off yet. Backend + API only, to keep pace with the other three features.
