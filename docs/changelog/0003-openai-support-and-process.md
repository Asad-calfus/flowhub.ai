# 0003 — OpenAI Provider Support, Safe-Spend Guardrails, and Process Changes

**Date**: 2026-07-21
**Status**: Complete

## What changed

1. Added OpenAI as a second LLM provider for the few-shot classifier, using JSON mode
   (`response_format={"type": "json_object"}`) to reduce invalid-JSON retries.
2. Added `src/classification/pricing.py`, a rough $/1M-token cost estimator, and made
   `scripts/run_llm.py` **safe by default**: it always dry-runs (no API calls) unless `--live`
   is passed explicitly, even if a real API key is configured. `--live` prints a pre-flight
   cost estimate and asks for `y/N` confirmation (skippable with `--yes`), and refuses to run
   if the configured provider's key isn't set.
3. Started this changelog convention: one dated doc per notable change, indexed from
   `CHANGELOG.md` at the repo root, going forward.
4. Initialized git and committed the existing work as a real history (Phase 1, Phase 2, then
   this change) instead of leaving it as an uncommitted working tree.

## Why

The user asked to use a real OpenAI key without risking accidental spend, wants a running
record of what changed and why after every notable change, and wants an actual git history
instead of one large uncommitted blob.

## Files added/changed

```
src/classification/pricing.py                  (new)
src/classification/classifier.py                (OpenAI branch, provider-aware API key lookup)
scripts/run_llm.py                              (--live/--yes flags, cost estimate + confirmation)
requirements.txt                                (+ openai)
.env.example                                    (OPENAI_API_KEY, LLM_PROVIDER=openai default)
README.md                                       (cost-optimized usage section)
tests/test_pricing.py                           (new)
tests/test_classifier.py                        (+ provider-selection and safe-default tests)
docs/changelog/0001-*.md, 0002-*.md, 0003-*.md  (new, retrospective + this change)
CHANGELOG.md                                    (new, index)
```

## How to verify

```bash
python3 -m pytest -q                    # 45/45 passing at the time of this change
python3 scripts/run_llm.py              # still dry-run by default
python3 scripts/run_llm.py --live       # aborts cleanly with no key configured
```

## Notable decisions

- Dry-run safety lives in the **script**, not the library: `FewShotClassifier` still respects
  an explicit `dry_run=False` if a caller wants it (needed for future automation), but
  `scripts/run_llm.py` never passes that unless `--live` is on the command line.
- Cost estimates are intentionally rough (`docs` comment in `pricing.py` says so) - they exist
  to catch "this will cost $4" mistakes, not to be exact.
- Recommended default model is `gpt-4o-mini` (cost-efficient, sufficient for a 30-record
  structured-classification task).

## Process going forward

- A dated doc under `docs/changelog/` is added after every notable change, indexed in
  `CHANGELOG.md`.
- Disposable/generated files (`.venv/`, `__pycache__/`, `.pytest_cache/`, `results/cache/`,
  `.env`) stay out of git via `.gitignore`; nothing generated is committed.
- Regular, scoped git commits (one per notable change) replace large uncommitted batches of
  work.

## Follow-ups deferred to later phases

Embeddings, clustering, context matching, weekly summaries, API/database/frontend - unchanged
from Phase 2's deferral list.
