# 0001 — Phase 1: Synthetic Dataset Foundation

**Date**: 2026-07-21
**Status**: Complete

## What changed

Created the initial synthetic dataset for the fictional FlowHub SaaS product: 150
hand-authored feedback records, a 30-record manually-reviewed gold evaluation subset, and
four product context files (modules, known bugs, feature requests, releases).

## Why

Real feedback data doesn't exist yet (the product is fictional) and shouldn't be simulated
with real customer data. A synthetic dataset lets categorization/sentiment/theme-detection
work be designed and evaluated against known-correct labels before any classifier exists.

## Files added

```
data/raw/synthetic_feedback.csv
data/processed/feedback_dataset.csv
data/evaluation/gold_feedback.csv
data/context/{product_modules,known_bugs,feature_requests,product_releases}.csv
data/README.md
docs/{dataset_plan,taxonomy,data_dictionary,dataset_summary}.md
scripts/generate_dataset.py
scripts/validate_dataset.py
```

## How to verify

```bash
python3 scripts/generate_dataset.py   # regenerates all CSVs deterministically
python3 scripts/validate_dataset.py   # 23 integrity checks, all should PASS
```

## Notable decisions

- `category` is a deterministic roll-up of `feedback_type` (see `docs/data_dictionary.md`),
  not an independently authored label.
- Evaluation-label fields (`feedback_type`, `category`, `product_module` as originally
  labeled, `sentiment`, `urgency`, `theme_hint`, `related_context_id`, `is_gold_label`,
  `label_source`) were documented up front specifically so Phase 2 could enforce a
  data-leakage rule against them.
- 69 of 150 records were deliberately grouped into 8 recurring themes to support future
  clustering work; the rest are one-off issues, including 82 with no known-bug/feature-request
  match at all (to avoid the dataset skewing toward "already known" problems).

## Follow-ups deferred to later phases

Embeddings, clustering, context retrieval, and any classifier were explicitly out of scope
for this phase.
