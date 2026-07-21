# Project Context — FlowHub AI Customer Feedback Intelligence Platform

**Purpose of this doc**: a single entry point summarizing everything built so far, so the
next phase can start without re-reading the whole repo. It's a snapshot/index, not the
authoritative source for any topic - follow the links for detail, and treat this doc as
possibly stale on anything it doesn't link to a source file for.

**Last updated**: 2026-07-21, after `docs/changelog/0006`.

**Roadmap**: see `docs/project_plan.md` for the full 10-phase plan, MVP scope, deferred
features, and the "changes from the original plan" record. This doc is current status; that
one is where we're headed.

## The product (fictional)

**FlowHub** - a project management / team collaboration SaaS. 8 modules: Authentication,
Dashboard, Task Management, Notifications, Billing, Integrations, Reports, Mobile App.
6 releases (`v2.1.0`-`v2.6.0`, Jan-Jul 2026). Defined in `data/context/*.csv`.

## What exists today

### Phase 1 — Synthetic dataset (`docs/changelog/0001-*.md`)

150 hand-authored feedback records + 30 manually-reviewed gold subset + product context
(15 known bugs, 12 feature requests, 6 releases, 8 modules). Deliberately varied: tone,
length, grammar, 5 non-English records, near-duplicates, similar-wording-different-meaning
pairs, 8 recurring themes (69 of 150 records) for future clustering work.

- Full schema: `docs/dataset/data_dictionary.md`
- Label definitions + ambiguous-case rulings: `docs/dataset/taxonomy.md`
- Design rationale + leakage rule origin: `docs/dataset/dataset_plan.md`
- Current stats: `docs/dataset/dataset_summary.md`
- Regenerate/validate: `scripts/data/generate_dataset.py`, `scripts/data/validate_dataset.py`

### Phase 2 — Classification pipeline (`docs/changelog/0002-*.md`, `0003-*.md`)

Turns raw feedback text into structured output: `feedback_type`, `category`,
`product_module`, `sentiment`, `urgency`, `confidence`, `reasoning`. Two implementations:

- **Rule-based + VADER baseline** (`src/classification/baseline.py`) - deterministic, no
  API calls, exists only as a comparison floor.
- **Few-shot LLM classifier** (`src/classification/classifier.py`) - supports OpenAI (JSON
  mode) and Anthropic, strict Pydantic validation (`src/classification/schemas.py`), one
  retry on invalid output, local caching by `feedback_id`, dry-run stub for cost-free
  iteration.

**Data-leakage rule, enforced in code**: classifier input is restricted to `feedback_text`,
`source`, `customer_tier`, `product_version`, `rating`, `language`.
`assert_no_leakage()`/`ClassifierInput` reject any of `feedback_type`, `category`,
`product_module`, `sentiment`, `urgency`, `theme_hint`, `related_context_id`,
`is_gold_label`, `label_source` if they appear in a payload headed for a prompt. Note
`product_module` is a *target to predict* in Phase 2, even though Phase 1's data dictionary
listed it as an input - that's an intentional change, not a contradiction.

Few-shot examples are drawn only from the 120 non-gold records (`select_few_shot_examples`
raises if a gold record leaks into that pool). Evaluation (`src/classification/evaluator.py`)
runs only against the 30 gold records and computes per-field accuracy, macro P/R/F1, and
confusion matrices, plus run-level stats (schema success rate, retries, failures, latency,
token usage).

**Current results** (baseline; LLM numbers are identical right now because no live API key
has been used yet - `llm_predictions.csv` reflects the dry-run stub, not a real model):

| field | accuracy |
|---|---|
| feedback_type | 0.40 |
| category | 0.43 |
| product_module | 0.83 |
| sentiment | 0.27 |
| urgency | 0.43 |

Full breakdown and known failure modes: `results/error_analysis.md`. Sentiment is the
weakest field - VADER under-reacts to long, matter-of-fact negative support tickets. A real
LLM run is expected to improve most fields meaningfully; that hasn't been measured yet.

**Cost-safe real-key usage** (`docs/changelog/0003-*.md`): `scripts/pipeline/run_llm.py`
always dry-runs unless `--live` is passed explicitly; `--live` prints a cost estimate
(`src/classification/pricing.py`) and asks for confirmation. Recommended model: `gpt-4o-mini`.

### Repo structure tidy (`docs/changelog/0004-*.md`, `0006-*.md`)

`scripts/` split into `data/` and `pipeline/`; `docs/` split into `dataset/` and
`changelog/`; `tests/` mirrors `src/` (`tests/classification/`). This doc lives at
`PROJECT_CONTEXT.md` (root, moved from `docs/` in 0006 to sit alongside `README.md`/
`CHANGELOG.md`). No `pyproject.toml`/CI yet - explicitly deferred, not an oversight. Current
full layout is in the root `README.md` "Project structure" section.

## Process conventions in effect (see memory, not just this doc)

- A dated doc under `docs/changelog/` after every notable change, indexed in `CHANGELOG.md`.
- Regular, scoped git commits (one per notable change) on `main`, pushed to `origin`
  (`github.com/Asad-calfus/flowhub.ai`).
- Generated/disposable files never committed: `.venv/`, `__pycache__/`, `.pytest_cache/`,
  `results/cache/`, `.env` (all in `.gitignore`).
- Real API keys only ever in `.env` (gitignored), never `.env.example`. Live LLM calls are
  opt-in (`--live`), cost-estimated, and confirmed before spending.

## Explicitly NOT built yet

Embeddings, similarity/similar-feedback search, theme clustering, context (bug/feature
request) matching against `related_context_id`, weekly summary generation, the API layer,
database, frontend, CI/CD, and packaging (`pyproject.toml`). These were deferred by explicit
decision at each phase, not forgotten - see the "Follow-ups deferred" section of each
changelog entry.

## Quick orientation for a fresh session

1. Read this doc, then `README.md` for exact run commands.
2. If touching the dataset: `docs/dataset/data_dictionary.md` + `docs/dataset/taxonomy.md`
   first.
3. If touching the classifier: `src/classification/schemas.py` first (the leakage
   contract), then `results/error_analysis.md` for known weak points.
4. Run `python3 -m pytest -q` before and after any change (45 tests at last count).
5. Add a `docs/changelog/000N-*.md` entry + `CHANGELOG.md` line, then commit, before
   considering a change done.
