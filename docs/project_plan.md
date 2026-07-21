# Project Plan — FlowHub AI Customer Feedback Intelligence Platform

Main implementation roadmap. For current build status see `PROJECT_CONTEXT.md`; for
per-change detail see `docs/changelog/`. This doc says *what's planned*, not *what's true
right now* — don't duplicate detail that lives in those files.

## Objective

Analyze customer feedback for a fictional SaaS product (FlowHub): categorize it, detect
sentiment, find similar/duplicate feedback, match it to known bugs and feature requests,
surface recurring themes, and generate weekly product insights — with every AI step
evaluated against a hand-labeled gold set.

## Architecture direction

Local-first and incremental: each phase must run and be evaluated standalone before the next
one builds on it. No DB/API/frontend until the AI core (classification + retrieval +
clustering) is proven on the gold set. Prefer deterministic/local components (VADER,
sentence-transformers, sklearn) with an LLM only where a deterministic approach clearly can't
do the job (classification, weekly-summary prose).

## Roadmap

| # | Phase | Status |
|---|---|---|
| 1 | Synthetic dataset and taxonomy | Complete |
| 2 | Classification and sentiment pipeline | Complete |
| 3 | Embeddings, similarity search, and context matching | Complete |
| 4 | Theme clustering and trend detection | Current |
| 5 | PostgreSQL and FastAPI layer | Planned |
| 6 | Weekly insight generation | Planned |
| 7 | Frontend dashboard | Planned |
| 8 | Background processing (Celery + Redis) | Planned |
| 9 | Human corrections and final evaluation | Planned |
| 10 | Deployment and documentation | Planned |

Each phase gets its own changelog entry (or several) on completion; this table's Status
column is the source of truth for "what phase are we in."

## MVP features

Classify feedback (type/category/module/sentiment/urgency) → find similar feedback → match
against known bugs/feature requests → cluster into themes → weekly summary → basic dashboard
to browse it all, with human correction feeding back into evaluation.

## Deferred (explicitly, not forgotten)

Vector databases (pgvector later, not now), LangChain/LlamaIndex, multi-org support, Jira/
Slack integrations, churn prediction, AI copilot, scheduled alerts — none of these are on the
roadmap above; revisit only after phase 10.

## Technical stack

- **AI/NLP**: few-shot LLM (OpenAI or Anthropic) for classification; VADER for a baseline;
  `sentence-transformers/all-MiniLM-L6-v2` for embeddings (phase 3); scikit-learn for
  clustering (phase 4).
- **Backend** (phase 5+): FastAPI, Pydantic, SQLAlchemy + Alembic.
- **Database** (phase 5+): PostgreSQL, pgvector.
- **Background jobs** (phase 8+): Celery + Redis.
- **Frontend** (phase 7+): Next.js, TypeScript, Tailwind, Recharts.
- **Deployment** (phase 10): Docker Compose.

## Data-leakage rule (applies to every phase)

Evaluation-label fields — `feedback_type`, `category`, `product_module`, `sentiment`,
`urgency`, `theme_hint`, `related_context_id`, `is_gold_label`, `label_source` — are never
passed as input to any classifier, embedder, or retrieval step. Each phase enforces this in
code (see `src/classification/schemas.py::assert_no_leakage` for the phase 2 pattern) and adds
tests proving it, not just a docstring promise.

## Testing requirements

- Every phase ships with `pytest` tests covering: leakage prevention, schema/output
  validation, and its own core logic (see `tests/classification/` for the phase 2 pattern).
- Run the full suite before and after any change; it must stay green.
- Tests mirror `src/` structure (`tests/<package>/test_*.py`).

## Git and changelog conventions

- One dated `docs/changelog/000N-*.md` per notable change, indexed in `CHANGELOG.md`.
- One scoped git commit per notable change — no large uncommitted batches.
- Generated/disposable files (`.venv/`, `__pycache__/`, `results/cache/`, `.env`) never
  committed.
- Real API keys only in `.env` (gitignored); live LLM calls are opt-in and cost-estimated.

## Changes made from the original plan

The original pre-build plan (public + synthetic data, 300–500 records, 50–100 gold records,
full architecture speced up front) was revised once dataset work actually started:

- **Public datasets → fully synthetic.** Avoids licensing/privacy issues and guarantees every
  label is known-correct, at the cost of realism being designed rather than observed.
- **300–500 records → 150.** Enough variety to exercise every planned AI step without the
  overhead of authoring/reviewing a much larger set by hand.
- **50–100 gold records → 30.** Sized for thorough manual review (every ambiguous case
  checked) rather than statistical power; revisit if a later phase needs tighter confidence
  intervals.
- **Fictional product defined**: FlowHub, a PM/collaboration SaaS, invented specifically so
  feedback text, bugs, features, and releases could stay internally consistent.
- **Dataset generation/validation scripts added** (`scripts/data/`) — not in the original
  plan, added because hand-writing 150+30 CSV rows without a deterministic generator/checker
  risked ID collisions and label drift.
- **Product context files (bugs/features/releases) built alongside the dataset**, earlier
  than the original "Implementation Order" suggested, since retrieval/matching (phase 3)
  needs them and they were cheap to define at the same time as the feedback records.

Everything else (classification approach, tech stack, phase ordering after phase 3) is
unchanged from the original intent.
