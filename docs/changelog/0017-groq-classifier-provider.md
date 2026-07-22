# 0017 — Groq provider for the classifier + first live LLM run

**Date**: 2026-07-22
**Status**: Complete

## What changed

Added `"groq"` as a third supported provider in `FewShotClassifier`
(`backend/src/classification/classifier.py`), then ran `scripts/pipeline/run_llm.py --live`
for real against the 30 gold records.

- **Groq support**: `_api_key_env_var()` maps `"groq" -> "GROQ_API_KEY"`. `_call_llm()` routes
  `"groq"` through the existing `_call_openai()` path (Groq's chat-completions API is
  OpenAI-compatible), with a new `GROQ_BASE_URL` constant
  (`https://api.groq.com/openai/v1`) passed to the `openai.OpenAI` client only when
  `provider == "groq"`. No duplicated request logic.
- **Pricing** (`src/classification/pricing.py`): added an approximate `llama-3.1-8b-instant`
  entry and set it as Groq's `RECOMMENDED_MODEL`, so `run_llm.py --live`'s pre-flight cost
  estimate still works for this provider.
- **Env** (`backend/.env`, not committed): `LLM_PROVIDER=groq`, `LLM_MODEL=llama-3.1-8b-instant`,
  `GROQ_API_KEY` set to a real key provided by the user for this purpose.
  `backend/.env.example` documents the new `GROQ_API_KEY` var and flags that the Phase 6
  weekly-report LLM narrative generator (`src/reports/generator.py::LLMReportGenerator`,
  a separate, duplicated implementation) does **not** yet support `"groq"` - out of scope
  this pass, since the ask was specifically the classification pipeline.
- **Tests**: `test_groq_provider_selects_groq_api_key_env_var` and
  `test_groq_provider_uses_openai_client_with_groq_base_url` added to
  `tests/classification/test_classifier.py`.

## Why

User request: get the classification pipeline actually calling a real LLM, using a Groq key
they already had. Confirmed scope (classification pipeline only, not the report narrative or
the self-serve workspace flow) and provider/key before doing anything that could spend money.

## Results — real numbers now exist

30/30 gold records classified live, 0 failures, 1 retry (schema success rate 1.0). Stored as
`analysis_results` rows (`model_name='groq:llama-3.1-8b-instant'`) and one `evaluation_runs`
row. Meaningfully better than the rule-based baseline on every field except
`product_module` (already near-ceiling):

| field | baseline | live LLM | delta |
|---|---|---|---|
| feedback_type | 0.40 | 0.67 | +0.27 |
| category | 0.43 | 0.73 | +0.30 |
| product_module | 0.83 | 0.87 | +0.03 |
| sentiment | 0.27 | 0.60 | +0.33 |
| urgency | 0.43 | 0.60 | +0.17 |

Full per-field precision/recall/F1 and confusion matrices are in `evaluation_runs.metrics_json`.
`PROJECT_CONTEXT.md`'s Phase 2 section updated with this table (was previously flagged as "not
measured yet").

## Verification

- `pytest -q`: 188/188 passing (186 prior + 2 new Groq tests). One pre-existing test
  (`test_live_llm_without_api_key_returns_503`) needed a fix - see Notable decisions.
- Manual: `python3 scripts/pipeline/run_llm.py --live --yes --force` against the real dev DB;
  confirmed via `psql` that `evaluation_runs.dry_run = false` and 30 `analysis_results` rows
  have `model_name = 'groq:llama-3.1-8b-instant'`.

## Notable decisions

- **`classify()` checks the local cache before checking dry-run/live.** The first `--live`
  attempt (without `--force`) silently served all 30 records from
  `results/cache/llm_cache.json`, which had been populated by an earlier dry-run - so it
  "succeeded" with `dry_run=true` in the output and zero real API calls. Cache hits are
  keyed only by `feedback_id`, not by provider/model/dry_run state, so switching from
  dry-run to live (or between providers) on already-cached records requires `--force`. This
  is pre-existing behavior, not introduced here, but worth documenting since it's an easy
  trap - now called out in `PROJECT_CONTEXT.md`.
- **Fixed `test_live_llm_without_api_key_returns_503`** to explicitly `monkeypatch.delenv()`
  all three provider key env vars and reset `analysis_service._llm_classifier` to `None`,
  rather than relying on the ambient `.env` having no key configured. That assumption broke
  the moment a real `GROQ_API_KEY` was added for this task - the test's intent (no key ->
  503) was correct, its isolation wasn't.
- **Groq rate limits caused real wall-clock delay** (~14s/call with frequent 429-retry-after-14s
  cycles for the first ~20 records, then fast for the rest) - nothing to fix, just a real
  characteristic of the free/low tier, noted here so a future run isn't mistaken for a hang.

## Follow-ups deferred

`LLMReportGenerator` (weekly-report narrative) and the self-serve workspace's "Process my
data" step (`docs/changelog/0015-*.md`) both still default to baseline/no Groq support -
explicitly out of scope this round, per confirmed scope.
