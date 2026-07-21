# FlowHub AI Customer Feedback Intelligence Platform

Starting a new phase or a fresh session? Read `PROJECT_CONTEXT.md` first - it's a
single-page summary of everything built so far and what's explicitly not built yet.

## Project structure

```text
data/                   # dataset (raw/processed/evaluation/context) - see data/README.md
docs/
├── dataset/            # dataset design docs (plan, taxonomy, data dictionary, summary)
└── changelog/          # one dated doc per notable change, indexed by CHANGELOG.md
results/                # predictions, metrics, error analysis (generated, not hand-written)
scripts/
├── data/               # generate/validate the dataset
└── pipeline/           # run baseline / LLM classifier / evaluation
src/
├── data_loader.py       # shared CSV loading helpers
└── classification/      # schemas, prompt builder, baseline, LLM classifier, evaluator, pricing
tests/
└── classification/      # mirrors src/classification/
```

## Phase 1 — Synthetic dataset

See `data/README.md` and `docs/dataset/` (`dataset_plan.md`, `taxonomy.md`,
`data_dictionary.md`, `dataset_summary.md`) for the 150-record synthetic feedback dataset,
gold evaluation set, and product context files.

## Phase 2 — Classification and sentiment pipeline

A small pipeline that turns raw feedback text into validated structured output: feedback
type, category, product module, sentiment, and urgency. Two classifiers are implemented for
comparison - a deterministic rule-based + VADER baseline, and a few-shot LLM classifier with
strict Pydantic validation, retry, and local caching.

**Data-leakage rule (enforced in code, see `src/classification/schemas.py`)**: the classifier
only ever sees `feedback_text`, `source`, `customer_tier`, `product_version`, `rating`,
`language`. `product_module`, `feedback_type`, `category`, `sentiment`, `urgency`,
`theme_hint`, `related_context_id`, `is_gold_label`, and `label_source` are evaluation labels
only, and `assert_no_leakage()` raises if any of them reach a prompt payload.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY (or ANTHROPIC_API_KEY) only for a live LLM run
```

### Run the baseline (rule-based + VADER, no API calls, no cost)

```bash
python3 scripts/pipeline/run_baseline.py
```

### Run the few-shot LLM classifier

```bash
# Dry-run - ALWAYS the default, even if an API key is present. No network calls.
python3 scripts/pipeline/run_llm.py

# Live run: real API calls against the 30 gold records only. Prints a cost estimate
# and asks for confirmation before spending anything.
python3 scripts/pipeline/run_llm.py --live

# Live run, skip the confirmation prompt (e.g. non-interactive/CI use)
python3 scripts/pipeline/run_llm.py --live --yes

# Bypass the cache and reclassify everything (combine with --live to force fresh API calls)
python3 scripts/pipeline/run_llm.py --live --force
```

Predictions are cached by `feedback_id` in `results/cache/llm_cache.json`. Without `--force`,
any record with a valid cached prediction is skipped - re-running while debugging never
re-spends API calls. Only the 30 gold records are ever sent to the LLM; `--live` refuses to
run at all if the configured provider's API key isn't set.

### Using a real API key without overspending

The pipeline is designed so a real key is cheap and hard to spend accidentally:

1. **Dry-run is the script default, not just the library default.** `--live` is the only way
   to trigger a real call, regardless of whether a key is in `.env`.
2. **Cost is estimated and confirmed before any call is made.** `--live` prints an estimate
   (`src/classification/pricing.py`) for the records it's about to send, and prompts for `y/N`
   unless `--yes` is passed.
3. **Only 30 records, ever.** Every script targets `data/evaluation/gold_feedback.csv`
   exclusively - there is no code path that sends the full 150-record dataset to an LLM.
4. **Caching makes iteration free.** Once a gold record has a valid cached prediction, it's
   never re-sent unless you pass `--force`. Prompt/logic changes only cost tokens for the
   records actually affected if you clear just those cache entries.
5. **Use a cheap model.** Default recommendation in `.env.example` is `gpt-4o-mini`
   (`LLM_PROVIDER=openai`) - roughly $0.15 / $0.60 per 1M input/output tokens. For 30 short
   feedback records with a ~5-example few-shot prompt, a full `--live --force` run costs a
   fraction of a cent (see `results/evaluation_metrics.json` → `llm.run_summary` for actual
   token counts after a run, or `estimate_run_cost_usd()` for a pre-flight number).
6. **JSON mode reduces wasted retries.** The OpenAI path uses `response_format={"type":
   "json_object"}`, so malformed-JSON retries (which double the token cost of a record) should
   be rare in practice.
7. **Debug with `--dry-run` first, always.** Validate prompt/schema changes against the local
   stub before ever touching `--live`.

### Run evaluation (baseline vs. LLM, against the gold set)

```bash
python3 scripts/pipeline/run_evaluation.py
```

Writes `results/evaluation_metrics.json` (per-field accuracy, macro precision/recall/F1,
confusion matrices, and run-level stats: schema success rate, retries, failures, latency,
token usage) and prints a summary table.

### Run tests

```bash
python3 -m pytest -q
```

### Full pipeline in one go

```bash
python3 scripts/pipeline/run_baseline.py && python3 scripts/pipeline/run_llm.py && python3 scripts/pipeline/run_evaluation.py
```

### Outputs

```text
results/
├── baseline_predictions.csv
├── llm_predictions.csv
├── llm_failures.json         # stored, not skipped, JSON/schema failures
├── llm_run_meta.json         # model/provider/few-shot example IDs used
├── evaluation_metrics.json
└── error_analysis.md
```

## Not yet implemented

Embeddings, similarity search, theme clustering, context (bug/feature request) matching,
weekly summaries, the API layer, database, and frontend are out of scope for Phase 2 and are
planned for later phases.
