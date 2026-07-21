# 0007 — Phase 3: Embeddings and Context Retrieval

**Date**: 2026-07-21
**Status**: Complete

## What changed

Local semantic retrieval pipeline: embeds feedback and product-context records, finds
similar historical feedback, and matches feedback against known bugs/feature
requests/releases by cosine similarity with configurable thresholds. No LLM, no vector DB,
no clustering, no API/DB/frontend - all deferred per phase scope.

## Why

Needed before theme clustering (phase 4) and to let feedback link to existing bugs/feature
requests without an LLM call per record.

## Embedding model

`sentence-transformers/all-MiniLM-L6-v2` (`EMBEDDING_MODEL` env var to change it) - local, no
API cost, 384-dim, fast enough at this dataset size. Vectors are L2-normalized so cosine
similarity is a plain dot product.

## Files added

```
src/retrieval/{schemas,text_builder,embedder,similarity,context_retriever,evaluator}.py
scripts/pipeline/{generate_embeddings,run_similarity_search,evaluate_retrieval}.py
tests/retrieval/test_{leakage,embedder,similarity,context_retriever,evaluator}.py
results/retrieval/{similar_feedback_predictions.csv,context_match_predictions.csv,
                    retrieval_metrics.json,retrieval_error_analysis.md}
```
`results/retrieval/cache/` added to `.gitignore` (raw vectors + hash metadata, regenerable).

## How to verify

```bash
python3 scripts/pipeline/generate_embeddings.py
python3 scripts/pipeline/run_similarity_search.py
python3 scripts/pipeline/evaluate_retrieval.py
python3 -m pytest -q   # 65/65 passing at the time of this change
```

## Results (30 gold records)

Context matching: recall@1 = 0.83, recall@3 = 1.0, MRR = 0.90, false-known-issue rate on
genuinely new issues = 0.33. Similar feedback (all 150 records): same-theme precision/
recall@5 = 0.66. Details and specific miss cases: `results/retrieval/retrieval_error_analysis.md`.

## Notable decisions

- Leakage guard reused from `src/classification/schemas.py` rather than duplicated;
  `build_feedback_text()` whitelists exactly `feedback_text`/`source`/`customer_tier`/
  `product_version`/`language` and calls `assert_no_leakage()` on that whitelist.
- `retrieve_context()` never takes `related_context_id`/`theme_hint` as a parameter -
  evaluation reads them only in `evaluate_retrieval.py`, after the fact.
- Status derivation ranks bugs/features/releases in one pooled comparison, which means a
  release can occasionally outrank a correct bug match in the final `status` label even
  though recall@k (computed over bugs+features only) still counts it correctly - documented
  as a known nuance in the error analysis, not fixed in this phase.
- Cache stores vectors (`.npy`) and metadata/hashes (`.json`) separately, skipping re-encode
  for unchanged text.

## Follow-ups deferred

Theme clustering (phase 4), per-type similarity thresholds instead of one pooled ranking,
multilingual embedding model (the 1 non-English gold record embeds noticeably worse),
raising `CONTEXT_MATCH_THRESHOLD` to reduce the false-known-issue rate.
