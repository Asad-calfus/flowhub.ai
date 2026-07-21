# 0004 — Project Structure Tidy: Group Scripts, Docs, and Tests by Concern

**Date**: 2026-07-21
**Status**: Complete

## What changed

Reorganized folders for clarity without changing packaging (no `pyproject.toml`, `src/` is
still not pip-installable - that was an explicit choice, not an oversight):

- `scripts/` split into `scripts/data/` (dataset generation/validation) and
  `scripts/pipeline/` (baseline/LLM/evaluation runners).
- `docs/` split into `docs/dataset/` (dataset plan, taxonomy, data dictionary, summary) and
  `docs/changelog/` (unchanged, already grouped).
- `tests/` now mirrors `src/`: classification tests moved to `tests/classification/`.

No file content changed beyond fixing path-depth math (`BASE_DIR`/`sys.path.insert` needed
one more `dirname()` level after scripts moved one directory deeper) and updating path
references in docs/README.

## Why

User asked for a production-grade structure from the start and for docs/scripts/tests to be
grouped by concern instead of flat directories, while explicitly choosing NOT to introduce
packaging (`pyproject.toml`) or CI tooling yet - those are deferred until there's an actual
deploy target.

## Files moved (via `git mv`, history preserved)

```
scripts/generate_dataset.py   -> scripts/data/generate_dataset.py
scripts/validate_dataset.py   -> scripts/data/validate_dataset.py
scripts/run_baseline.py       -> scripts/pipeline/run_baseline.py
scripts/run_llm.py            -> scripts/pipeline/run_llm.py
scripts/run_evaluation.py     -> scripts/pipeline/run_evaluation.py
docs/dataset_plan.md          -> docs/dataset/dataset_plan.md
docs/taxonomy.md              -> docs/dataset/taxonomy.md
docs/data_dictionary.md       -> docs/dataset/data_dictionary.md
docs/dataset_summary.md       -> docs/dataset/dataset_summary.md
tests/test_baseline.py        -> tests/classification/test_baseline.py
tests/test_classifier.py      -> tests/classification/test_classifier.py
tests/test_evaluator.py       -> tests/classification/test_evaluator.py
tests/test_leakage.py         -> tests/classification/test_leakage.py
tests/test_prompt_builder.py  -> tests/classification/test_prompt_builder.py
tests/test_pricing.py         -> tests/classification/test_pricing.py
tests/test_schemas.py         -> tests/classification/test_schemas.py
```

New: `tests/classification/__init__.py`. Updated: `README.md` (new project-structure section
+ all script paths), `data/README.md` (doc/script path references).

## How to verify

```bash
python3 -m pytest -q                              # 45/45 passing, discovered recursively
python3 scripts/data/validate_dataset.py          # 23/23 checks passing
python3 scripts/pipeline/run_baseline.py
python3 scripts/pipeline/run_llm.py
python3 scripts/pipeline/run_evaluation.py
```

## Notable decisions

- `pytest.ini`'s `testpaths = tests` needed no change - pytest discovers `test_*.py`
  recursively by default.
- Historical changelog entries (0001-0003) were left describing paths as they existed at the
  time, rather than rewritten to match the new layout - they're a record of what happened,
  not living documentation.
- `src/classification/` was left as-is (already a well-scoped subpackage); `src/data_loader.py`
  stays a top-level utility since it isn't classification-specific.

## Follow-ups deferred

`pyproject.toml`/installable package, CI (GitHub Actions), and lint/format tooling were
explicitly deferred - revisit once there's a real deploy target or the test suite outgrows
plain `pytest`.
