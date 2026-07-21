# 0002 — Phase 2: Feedback Classification and Sentiment Pipeline

**Date**: 2026-07-21
**Status**: Complete

## What changed

Built a small classification pipeline that turns raw feedback text into validated structured
output (`feedback_type`, `category`, `product_module`, `sentiment`, `urgency`, `confidence`,
`reasoning`), with two implementations for comparison: a deterministic rule-based + VADER
baseline, and a few-shot LLM classifier (Anthropic, at the time) with strict Pydantic
validation, one retry on invalid output, and local caching. Evaluated both against the
30-record gold set.

## Why

Before wiring up embeddings/clustering/context-matching, we need a working, testable
classification step with measurable accuracy and a hard guarantee that evaluation labels
never leak into the model's input.

## Files added

```
src/data_loader.py
src/classification/{schemas,prompt_builder,baseline,classifier,evaluator}.py
scripts/{run_baseline,run_llm,run_evaluation}.py
tests/test_{leakage,schemas,baseline,classifier,prompt_builder,evaluator}.py
requirements.txt, .env.example, pytest.ini, .gitignore
results/{baseline_predictions.csv,llm_predictions.csv,llm_failures.json,llm_run_meta.json,
         evaluation_metrics.json,error_analysis.md}
```

## How to verify

```bash
python3 scripts/run_baseline.py
python3 scripts/run_llm.py            # dry-run, no API calls
python3 scripts/run_evaluation.py
python3 -m pytest -q                  # 37/37 passing at the time of this change
```

## Notable decisions

- **Leakage guard is enforced in code**, not just convention: `ClassifierInput` only accepts
  `feedback_text`, `source`, `customer_tier`, `product_version`, `rating`, `language`;
  `assert_no_leakage()` raises `LeakageError` if any evaluation-label field reaches a prompt
  payload. Note this treats `product_module` as a *target* to predict in Phase 2, which is a
  deliberate change from how Phase 1's data dictionary described it (as an input) - the
  incoming-feedback form no longer pre-tags a module; the classifier must infer it from text.
- Few-shot examples are drawn only from the 120 non-gold records, with a defensive check that
  raises if a gold record ever ends up in that pool.
- Dry-run mode reuses the rule-based baseline as a local stub so the full
  parse → validate → retry → cache path is exercised without any network call.
- Macro precision/recall/F1 and confusion matrices are computed by hand (no sklearn
  dependency) since the label sets are small.

## Baseline results (30 gold records)

| field | accuracy | macro F1 |
|---|---|---|
| feedback_type | 0.40 | 0.39 |
| category | 0.43 | 0.42 |
| product_module | 0.83 | 0.84 |
| sentiment | 0.27 | 0.20 |
| urgency | 0.43 | 0.32 |

Full breakdown in `results/error_analysis.md`. No live LLM run was performed in this change
(no API key was available in the environment) - `llm_predictions.csv` reflects the dry-run
stub, which is numerically identical to the baseline.

## Follow-ups deferred to later phases

Embeddings, similarity search, theme clustering, context (bug/feature-request) matching,
weekly summaries, API layer, database, and frontend.
