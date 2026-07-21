# Data — AI Customer Feedback Intelligence Platform (Phase 1)

Synthetic dataset for **FlowHub**, a fictional project management and team collaboration
SaaS product. All data here is generated for development and evaluation purposes — nothing
is derived from real customers.

## Folder structure and purpose

```
data/
├── raw/synthetic_feedback.csv       # Unmodified generator output — the original 150 records
├── processed/feedback_dataset.csv   # Canonical dataset used by all later phases
├── evaluation/gold_feedback.csv     # 30 manually reviewed records, a subset of processed/
└── context/                         # Product knowledge the feedback references
    ├── product_modules.csv
    ├── known_bugs.csv
    ├── feature_requests.csv
    └── product_releases.csv
```

### `raw/` vs. `processed/`

For this phase they are identical in content and schema — no cleaning step has been applied
yet. The split exists so that future phases (deduplication, normalization, text cleaning)
have a clear place to write transformed output (`processed/`) without overwriting the
original generated data (`raw/`). Treat `raw/` as append-only/immutable going forward.

### `evaluation/`

`gold_feedback.csv` contains 30 records selected from `processed/feedback_dataset.csv` and
manually reviewed (`is_gold_label = True`, `label_source = Manually verified`). It carries
one extra column, `gold_notes`, explaining why each record was picked (angry feedback, short
feedback, ambiguous case, known bug, new issue, duplicate feature request, release-related
problem, similar wording with a different meaning, etc.). Use this file to sanity-check
classifier output during development — it is not meant for training.

### `context/`

Ground-truth product knowledge that some feedback records reference via `related_context_id`
(a `bug_id` or `request_id`). This lets evaluation check whether a future pipeline correctly
links new feedback to an existing known bug or feature request, versus correctly recognizing
it as a new issue.

## Dataset limitations

- Small by design (150 feedback records) — enough for development and spot-checking, not for
  statistically robust model training or benchmarking.
- Distributions (feedback type mix, sentiment skew, module coverage) reflect deliberate
  design choices meant to exercise the future pipeline, not measured real-world traffic.
- Only 5 records are non-English; multilingual support is only lightly exercised.
- All 15 known bugs, 12 feature requests, and 6 releases are fictional and simplified
  compared to a real product's backlog.

## Privacy rules

- No real names, emails, phone numbers, or other personal information appear anywhere in
  this dataset. `customer_id` values are synthetic identifiers (`CUST-####`) with no link to
  any real person.
- Do not add real customer data to these files. If real feedback is ever incorporated in a
  later phase, it must be anonymized before being merged into a shared schema like this one.

## How this dataset will be used in later phases

- **Phase 2+ (categorization, sentiment, few-shot classification)**: only the *input* fields
  documented in `../docs/dataset/data_dictionary.md` should be passed to a classifier. The label
  fields
  (`feedback_type`, `category`, `sentiment`, `urgency`, `theme_hint`, `related_context_id`,
  `is_gold_label`, `label_source`) exist purely to score predictions against and must never be
  fed in as input — see `../docs/dataset/dataset_plan.md` for the data-leakage rule.
- **Similar-feedback search**: the deliberate near-duplicate and similar-wording-different-
  meaning records support testing whether a search/embedding approach can tell genuinely
  similar feedback apart from superficially similar but semantically different feedback.
- **Theme detection**: the 8 recurring themes (69 of the 150 records) give a clustering
  approach real structure to recover; `theme_hint` is the ground truth to check against, not
  an input.
- **Weekly summaries**: `created_at` timestamps span roughly January-July 2026 across all 6
  releases, enough to slice the dataset into weekly windows for summary generation.
- **Evaluation**: `data/evaluation/gold_feedback.csv` is the reference set for measuring
  classifier accuracy once a pipeline exists.

## Validation

Run `python3 scripts/data/validate_dataset.py` (from `backend/`) from the repository root to check dataset
integrity (unique IDs, valid label values, valid context references, correct record counts,
etc.). See `../docs/dataset/dataset_summary.md` for current statistics.
