# 0009 — Phase 4: Theme Clustering and Trend Detection

**Date**: 2026-07-21
**Status**: Complete

## What changed

Added `backend/src/themes/` (clustering, keywords, representatives, naming, trends,
evaluator, schemas) and two pipeline scripts, reusing Phase 3's cached feedback embeddings -
no regeneration, no LLM calls, no new label input to any AI step.

- **Clustering**: `AgglomerativeClustering` (cosine distance, average linkage) over the 150
  feedback embeddings only. `THEME_DISTANCE_THRESHOLD=0.55`, `THEME_MIN_SIZE=4` (both
  env-overridable, centralized in `src/themes/clustering.py`). Clusters below the minimum
  size stay unclustered rather than being forced into a theme. Deterministic: no randomness
  in agglomerative clustering, and theme numbering (`THM-001`, `THM-002`, ...) is assigned
  by descending cluster size with a smallest-member-id tiebreak, so re-running with the same
  inputs reproduces the same ids regardless of internal label order.
- **Keywords**: TF-IDF (`scikit-learn`) fit over all 150 `feedback_text` values, ranked per
  theme by mean weight within that theme's texts. Extended the stopword list with casual
  filler words (`like`, `really`, `just`, `pls`, `app`, ...) that otherwise polluted names.
- **Representatives**: top-3 members per theme by cosine similarity to the cluster centroid
  (not shortest-text), deterministic id tiebreak on exact ties.
- **Naming**: deterministic - top TF-IDF keywords + dominant product module, capped at 4
  words, module prepended only if not already implied by a keyword. No LLM.
- **Trends**: weekly (Monday-start) buckets per theme with count, change, percent change,
  sentiment/tier/module distributions, and a `new`/`growing`/`stable`/`declining` status
  (`>+20%` / `<-20%` / else stable; first week for a theme is always `new`).
- **Evaluation**: `theme_hint` read only in `evaluate_clustering()`, after clustering has
  already run - coverage, unclustered %, purity, ARI, NMI, pairwise P/R/F1, fragmented true
  themes, and mixed/incoherent predicted themes.

## Why

Phase 4 of `docs/project_plan.md` - group feedback into customer-readable themes and surface
basic trends, entirely locally, before any DB/API/frontend work.

## Files changed

```
backend/src/themes/{schemas,clustering,keywords,representatives,naming,trends,evaluator}.py  (new)
backend/scripts/pipeline/{generate_themes,evaluate_themes}.py                                  (new)
backend/tests/themes/{test_clustering,test_keywords,test_representatives,test_naming,
                       test_trends,test_evaluator,test_leakage}.py                              (new, 33 tests)
backend/results/themes/{theme_assignments.csv,themes.csv,theme_metrics.json,
                         theme_error_analysis.md}                                              (new, generated)
backend/requirements.txt        (added scikit-learn>=1.5)
README.md, PROJECT_CONTEXT.md, docs/project_plan.md   (Phase 4 status + summary)
```

## Results

16 themes from 150 records, 84 assigned / 66 unclustered (44%). Against the 69 records with
a `theme_hint`: cluster purity 0.92, ARI 0.38, NMI 0.70, pairwise precision/recall/F1
0.85/0.36/0.51, 3 fragmented true themes, 0 mixed predicted themes. Full breakdown, including
the `THM-001` login/mobile-crash merge and the Integrations-theme coverage gap:
`backend/results/themes/theme_error_analysis.md`.

## How to verify

```bash
cd backend
python3 scripts/pipeline/generate_themes.py     # writes theme_assignments.csv, themes.csv, theme_metrics.json
python3 scripts/pipeline/evaluate_themes.py     # adds the "evaluation" section to theme_metrics.json
python3 -m pytest -q                            # 98/98 passing
# force regeneration with a different threshold:
THEME_DISTANCE_THRESHOLD=0.6 THEME_MIN_SIZE=5 python3 scripts/pipeline/generate_themes.py
```

## Notable decisions

- Threshold chosen by inspecting actual cluster composition against `theme_hint`, not just
  maximizing ARI/NMI - a grid search up to 0.72 scored higher on both metrics but produced a
  32-member blob merging several unrelated true themes, which the phase's "avoid incorrectly
  merged themes" goal rules out even though it scores well in aggregate.
- Label fields (`theme_hint`, `sentiment`, `product_module`, etc.) are read for *reporting*
  (sentiment/module distributions, weekly trends) after clustering has already produced
  assignments - this is not leakage, matching the same pattern Phase 3 used for
  `related_context_id` in its evaluator. Only `clustering.py`/`keywords.py`/`naming.py`/
  `representatives.py` are structurally restricted to ids+vectors+`feedback_text`, and
  `tests/themes/test_leakage.py` asserts their signatures never accept a label field.
- User asked about using a Groq API key for LLM calls in this phase; declined - Phase 4's
  spec explicitly forbids any LLM use (deterministic naming/clustering only). Deferred to
  Phase 6 (weekly summaries).

## Follow-ups deferred

PostgreSQL, FastAPI, weekly LLM summaries, frontend, Celery/Redis, authentication (Phases
5-8+, unchanged). Also deferred within theme clustering itself: per-theme adaptive
thresholds, a multilingual embedding model (non-English records stay unclustered), and
richer duplicate/fragmentation repair.
