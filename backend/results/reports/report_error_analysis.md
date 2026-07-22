# Weekly report — error analysis

Based on `RPT-0004` (deterministic, period 2026-05-04..2026-05-10) and its evaluation
(`report_evaluation.json`). See `docs/changelog/0011-*.md` for the full Phase 6 writeup.

## Automated evaluation results

`metric_correctness=True`, `theme_coverage=1.0`, `important_issue_coverage=1.0`,
`evidence_traceability_rate=1.0`, `unsupported_claim_count=0`,
`recommendation_support_rate=1.0`, `schema_success=True`. These are expected to be 1.0/0/True
by construction for the deterministic path, since `assemble_report` copies every number
straight from the evidence pack - this run mainly confirms the pipeline wiring, not
report *quality*. Quality requires either the manual rubric below or a live LLM run judged
against real prose.

## Missing important themes

None missed relative to the evidence pack (`theme_coverage=1.0`) - but the evidence pack
itself is capped at `MAX_THEMES=8`, so a period with more than 8 active themes will silently
drop the smallest ones from the report. Not observed in this run (only 6 themes existed in
the period) but worth watching once more weeks of data accumulate.

## Repeated insights

"Top Customer Pain Points" and "Growing Themes" overlap heavily (5 of the 6 pain-point
themes also appear as growing, since almost everything in a sparse period reads as "new").
This is
a labeling artifact of `_trend()`: with no previous-period baseline, every first-ever theme
is classified "new," and "new" is currently treated the same as "growing" for both sections.
Consider giving "new" its own report section or excluding it from "Growing Themes" once more
historical data exists to distinguish "genuinely growing" from "first time seen."

## Unsupported statements

None found (`unsupported_claim_count=0`) - expected, since every insight's evidence is
populated directly from the same aggregation pass that produced the numbers next to it.

## Weak recommendations

No recommended actions fired in this period (`recommended_actions=[]`) - none of the
known bugs/feature requests/releases reached `MIN_REPEAT_COUNT=3` matched reports, and no
theme/enterprise/low-confidence cluster crossed its threshold either. This is a direct
consequence of the data-coverage limitation below (most feedback in this period has no
stored classification or context match), not a flaw in the rule logic itself - the rules
were separately unit-tested with seeded data that does cross the thresholds
(`tests/reports/test_aggregator.py::test_recommended_action_triggered_for_repeated_known_bug`,
`::test_low_confidence_cluster_triggers_human_review_action`).

## Incorrect trend interpretation

Not observed in this run. Checked the edge case where an entity drops to zero after being
active the prior period (`_trend(0, 5)`) - it correctly returns `("declining", -100.0)`, not
"stable," since only `previous_count == 0` (nothing to compare against) takes the
new/stable branch; a real previous count of 0 feedback going to non-zero current out of
nowhere is the only case classified "new" or "stable" without a percent change.

## Poor representative-feedback selection

Representatives are picked by urgency rank then feedback_id (`evidence_builder._pick_representatives`)
- deterministic, but doesn't account for recency or text length/informativeness. A short,
uninformative High-urgency record could be selected over a longer, clearer Medium-urgency
one. Low-risk given the small representative count (3), but worth revisiting if reports are
read by non-technical stakeholders who need the clearest possible quote.

## Data limitations (systemic, not specific to this run)

- Only the 30 gold-set feedback records have stored `analysis_results` and `context_matches`
  in the current database (baseline classification and context-matching were only ever run
  against the gold set - see `docs/changelog/0010-*.md`). Any period dominated by non-gold
  records will show most feedback as "unclassified" and "not yet retrieval-processed," which
  is exactly what this run's Data Limitations section reports (8 of 11 feedback records in
  this period). This is a demo-dataset limitation, not a bug in the aggregator - it will
  disappear once `POST /api/v1/analysis/batch` and context-matching are run over the full
  150 records.
- `MIN_MODULE_SAMPLE=3` hides low-volume modules from "Most Negative Product Modules" -
  correct for avoiding noise, but means sparse periods can show an empty section (as seen
  here) even when a module truly has 100% negative sentiment on 1-2 records.

## Prompt improvements (for the LLM narrative path, not yet exercised live)

- The system prompt (`src/reports/prompt_builder.py`) should be tightened further once real
  model output is observed: add an explicit example of a rejected (invented-ID) response
  next to the schema, since few-shot counter-examples tend to reduce hallucinated references
  more reliably than a prose instruction alone (this pattern already helped in the Phase 2
  classifier prompt - see `docs/changelog/0002-*.md`).
- No live LLM call has been made yet (cost-safety - `--live` was never passed during this
  implementation). `generation_latency_seconds`/`input_tokens`/`output_tokens`/
  `estimated_cost_usd` in `report_evaluation.json` are `None` for this reason; a real run
  will need a follow-up evaluation pass to fill those in, plus the manual 1-5 rubric below.

## Manual rubric (fill in after reading `weekly_report.md`)

| Dimension | Score (1-5) | Notes |
|---|---|---|
| Correctness | _pending_ | |
| Clarity | _pending_ | |
| Usefulness | _pending_ | |
| Evidence quality | _pending_ | |
| Actionability | _pending_ | |
