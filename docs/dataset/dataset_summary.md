# Dataset Summary — Phase 1

Statistics computed directly from `data/processed/feedback_dataset.csv` (150 records) and
related context files. Regenerate by re-running `scripts/data/generate_dataset.py`; these numbers
will always match the actual CSV contents since both are produced by the same script.

## Totals

- **Total feedback records**: 150
- **Gold feedback records**: 30 (20% of the dataset)
- **Product modules**: 8
- **Known bugs**: 15
- **Feature requests**: 12
- **Product releases**: 6

## Records per feedback type

| feedback_type | count | % |
|---|---|---|
| Bug report | 44 | 29.3% |
| Feature request | 30 | 20.0% |
| Usability issue | 24 | 16.0% |
| Service complaint | 15 | 10.0% |
| Performance issue | 15 | 10.0% |
| Question | 10 | 6.7% |
| Praise | 8 | 5.3% |
| Other | 4 | 2.7% |

Roughly matches the recommended distribution (Bug reports ~30%, Feature requests ~20%,
Usability issues ~15%, Performance ~10%, Complaints ~10%, Questions ~7%, Praise ~5%, Other
~3%); Usability issue landed slightly above target (16% vs. ~15%) and Bug report slightly
below (29.3% vs. ~30%) due to a couple of records reading more naturally as usability
friction during authoring.

## Records per category (roll-up of feedback_type)

| category | count |
|---|---|
| Technical Issue | 59 |
| Product Feedback | 54 |
| Support Experience | 15 |
| Inquiry | 10 |
| Positive Feedback | 8 |
| Other | 4 |

## Records per sentiment

| sentiment | count | % |
|---|---|---|
| Negative | 73 | 48.7% |
| Neutral | 60 | 40.0% |
| Positive | 12 | 8.0% |
| Mixed | 5 | 3.3% |

Negative feedback dominates, as expected for a support/feedback dataset, but Neutral,
Positive, and Mixed are all represented with enough volume (60, 12, and 5 records
respectively) to test sentiment classification across all four classes.

## Records per urgency

| urgency | count | % |
|---|---|---|
| Low | 83 | 55.3% |
| Medium | 45 | 30.0% |
| High | 22 | 14.7% |

## Records per product module

| product_module | count |
|---|---|
| Dashboard | 36 |
| Task Management | 29 |
| Authentication | 18 |
| Billing | 17 |
| Integrations | 14 |
| Notifications | 13 |
| Mobile App | 12 |
| Reports | 11 |

Dashboard is the largest bucket partly because it's the default module for general/vague
feedback that doesn't name a specific area (see "Other" and generic UI complaints).

## Records per customer tier

| customer_tier | count | % |
|---|---|---|
| Pro | 95 | 63.3% |
| Enterprise | 32 | 21.3% |
| Free | 23 | 15.3% |

## Records per source

| source | count |
|---|---|
| Support ticket | 47 |
| Chat | 29 |
| Community post | 28 |
| App review | 17 |
| Survey | 15 |
| Email | 14 |

## Records per language

| language | count |
|---|---|
| en | 145 |
| es | 2 |
| de | 1 |
| fr | 1 |
| pt | 1 |

## Records per theme

| theme_hint | count |
|---|---|
| (none / no major theme) | 81 |
| Login failures after an update | 10 |
| Delayed notifications | 9 |
| Slow dashboard loading | 9 |
| Confusing billing charges | 9 |
| Mobile app crashes | 9 |
| Missing dark mode | 8 |
| Integration synchronization failures | 8 |
| Difficulty exporting reports | 7 |

69 of 150 records (46%) belong to one of the 8 major recurring themes, each with 7-10
records — enough per theme to support clustering evaluation without forcing every record
into an artificial theme.

## Context linkage

- **Known bug matches** (`related_context_id` starts with `BUG-`): 47 records, covering all
  15 known bugs.
- **Feature request matches** (`related_context_id` starts with `FR-`): 21 records, covering
  10 of the 12 feature requests (the two exceptions — `FR-005`, Released, and `FR-007`,
  Rejected — are instead referenced from Question/Praise/Service complaint records, which is
  more realistic than customers re-requesting something already shipped or rejected).
- **New issues with no context match**: 82 records (54.7%) — deliberately the majority, so
  the dataset isn't dominated by "already known" problems.

## Missing values

| field | missing count | reason |
|---|---|---|
| `rating` | 117 | By design, only populated for Survey and App review sources |
| `product_version` | 0 | Always populated |
| `theme_hint` | 81 | By design, only set for records belonging to a major theme |
| `related_context_id` | 82 | By design, blank for new issues with no known match |

All other fields are always populated (enforced by `scripts/data/validate_dataset.py`).

## Duplicates

- **Exact duplicate feedback text**: 0 (enforced by validation).
- **Near-duplicate feedback**: present by design within themed clusters (e.g. multiple
  independently worded "dashboard is slow" reports) — not counted mechanically, since "near"
  duplication is a judgment call, but visually inspectable within each `theme_hint` group.
- **Reused customer_id** (same customer submitting more than one piece of feedback):
  3 customers (`CUST-1007`, `CUST-1041`, `CUST-1057`) appear 2-3 times each; 146 of 150
  records have a unique customer.

## Class imbalance

- Feedback type is imbalanced by design (Bug report and Feature request together make up
  ~49% of the dataset; Other is only 4 records) — intentional, mirroring real support-data
  skew, but means per-class evaluation metrics (not just overall accuracy) matter for
  low-frequency classes like Praise and Other.
- Sentiment is imbalanced toward Negative/Neutral (89% combined) with Mixed being especially
  rare (5 records, 3.3%) — any sentiment classifier evaluation should watch Mixed-class
  recall specifically, since 5 examples is a thin signal.
- Product module distribution is moderately skewed (Dashboard 36 vs. Reports 11) — partly
  reflects real usage patterns (dashboard/task management are used constantly; reports less
  so) and partly reflects Dashboard being the fallback module for generic feedback.

## Dataset limitations (recap)

- Small scale (150 records) — suitable for development and qualitative evaluation, not for
  statistically powered benchmarking.
- Only 5 non-English records — multilingual handling is only lightly exercised.
- Sentiment/urgency/type labels were authored by hand alongside the text (not independently
  double-annotated), so while internally consistent, they reflect one reviewer's judgment
  calls on ambiguous cases (documented in `docs/dataset/taxonomy.md`).
