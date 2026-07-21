# Dataset Plan — Phase 1

## Why a synthetic dataset

Real customer feedback data is either unavailable at this stage (the product doesn't exist
yet) or would require handling private customer information (names, emails, account
details) that shouldn't flow through an experimental AI pipeline. A synthetic dataset lets us:

- Design categorization, sentiment, and theme labels **before** building the classifier, so
  we know exactly what "correct" looks like.
- Control the distribution of feedback types, sentiment, and difficulty so the dataset
  exercises every part of the future pipeline (few-shot classification, similar-feedback
  search, theme clustering, weekly summaries) instead of relying on whatever happened to
  come in organically.
- Avoid any privacy risk, since nothing in the dataset is derived from a real person or a
  real company's feedback.

The tradeoff is realism: synthetic text can only approximate the full messiness of real
customer language. See **Limitations** below.

## Dataset size

- 150 main feedback records (`data/processed/feedback_dataset.csv`)
- 30 manually reviewed gold evaluation records, a subset of the 150 (`data/evaluation/gold_feedback.csv`)
- 15 known bugs, 12 existing feature requests, 6 product releases, 8 product modules (`data/context/`)

This is intentionally small. The goal of Phase 1 is a dataset that is easy to read end to
end, verify by hand, and reason about — not a large-scale training corpus.

## Fictional product

**FlowHub** — a project management and team collaboration SaaS product, used consistently
across every feedback record and context file. It has 8 modules: Authentication,
Dashboard, Task Management, Notifications, Billing, Integrations, Reports, and Mobile App.
Six releases (v2.1.0 through v2.6.0, January–July 2026) introduce features and, in a few
cases, the bugs that later feedback complains about — this keeps feedback, bugs, feature
requests, and releases internally consistent instead of floating independently.

## Data-generation strategy

Every feedback record was hand-authored (not templated with mad-libs style substitution) to
avoid the repetitive phrasing and uniform tone that makes synthetic text easy to spot. Records
were built in two groups:

1. **Themed clusters** (69 records) — deliberately written in groups of 7-10 around eight
   recurring themes (e.g. "Login failures after an update", "Slow dashboard loading"), each
   tied to one or two entries in `known_bugs.csv` or `feature_requests.csv`. This gives the
   future clustering/theme-detection work real signal to find.
2. **Non-themed records** (81 records) — one-off bug reports, feature requests, usability
   issues, performance issues, complaints, questions, praise, and vague "other" feedback that
   don't belong to a major theme, some tied to remaining context entries and many left as
   genuinely new issues with no match.

A small Python script (`scripts/generate_dataset.py`) assembles the hand-written records into
the final CSVs and assigns `feedback_id`, `category`, and gold-label flags mechanically, so the
generated files are guaranteed to be internally consistent (no ID collisions, no orphaned
labels) even though the content itself was authored by hand.

## How realism and variety are maintained

- **Length**: from one-line reactions ("logged out again??") to multi-sentence Enterprise
  tickets with specifics (row counts, timestamps, version numbers).
- **Tone**: angry, polite-but-firm, neutral, casual, and enthusiastic messages are all present.
- **Grammar/style**: mixed capitalization, missing punctuation, informal chat-style phrasing,
  and typos appear alongside carefully written support tickets.
- **Technical knowledge**: some customers cite exact versions and row counts; others just say
  "it's slow" or "is something down?".
- **Language**: 5 records are written in Spanish, French, German, and Portuguese to test that
  the language field and any future pipeline step accounts for non-English input.
- **Duplicates and near-duplicates**: within each themed cluster, several records describe the
  same underlying issue in different words (e.g. multiple independent "dashboard is slow"
  reports), which is realistic and useful for similar-feedback search. No two records share
  exact, word-for-word text.
- **Similar wording, different meaning**: e.g. two "export" complaints — one about the CSV
  1000-row truncation bug, one requesting Excel formatting as a new feature — that a naive
  keyword-similarity search might wrongly conflate.

## Which fields are inputs vs. evaluation labels

Only the fields that would realistically be available the moment a new piece of feedback
arrives should ever be passed into a classifier:

**Input fields**: `feedback_text`, `source`, `created_at`, `customer_id`, `customer_tier`,
`product_module`, `product_version`, `rating`, `language`.

**Evaluation labels (never passed to the classifier as input)**: `feedback_type`, `category`,
`sentiment`, `urgency`, `theme_hint`, `related_context_id`, `is_gold_label`, `label_source`.

See `docs/data_dictionary.md` for the per-field breakdown.

## How data leakage will be prevented

- The label fields listed above exist only to score model output against — they are never
  fed into a prompt, feature vector, or embedding in later phases.
- `related_context_id` in particular is ground truth for evaluating context-matching
  (e.g. "did the model correctly link this feedback to BUG-011?") and must never be exposed as
  an input, since it would trivially leak the answer.
- Any future data loader for Phase 2+ should select columns explicitly (input columns only)
  rather than dropping label columns, so a schema change can't accidentally reintroduce a label.

## Limitations

- Synthetic text, however carefully varied, doesn't capture the full range of real customer
  phrasing, especially highly domain-specific jargon or truly chaotic multi-topic rants.
- Only 5 non-English records exist — nowhere near enough to evaluate multilingual performance
  properly, just enough to confirm the field and pipeline handle it without crashing.
- The 30-record gold set is small; it's meant for spot-checking classifier behavior, not for
  statistically rigorous evaluation.
- Distributions (feedback type, sentiment, module) were chosen by design, not sampled from
  real traffic, so they reflect assumptions about what a PM SaaS's feedback mix looks like
  rather than measured reality.
