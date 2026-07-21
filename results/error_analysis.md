# Error Analysis — Phase 2

Based on `results/baseline_predictions.csv` and `results/llm_predictions.csv` against the 30
gold records in `data/evaluation/gold_feedback.csv`.

**Note on the LLM run**: no `ANTHROPIC_API_KEY` was available in this environment, so
`llm_predictions.csv` was produced in **dry-run mode**, which uses the same rule-based +
VADER logic as the baseline as a local stub (see `src/classification/classifier.py`). Its
predictions are therefore identical to the baseline's in this run — the numbers below apply
to both files. Once a real API key is configured, re-run `python3 scripts/run_llm.py --force`
to get genuine LLM predictions and re-run evaluation; the LLM should meaningfully outperform
this rule-based baseline, particularly on `feedback_type` and `sentiment`.

## Common classification errors

**`feedback_type` defaults to "Other" whenever no keyword rule fires.** This is the single
biggest failure mode of the rule-based baseline: `FB-0001` ("get logged out... driving my
whole team crazy") and `FB-0073` ("Duplicating a project copies the tasks but not the custom
fields") contain no word from the hardcoded bug-keyword list (crash, broken, bug, error...),
so they fall through to `Other` instead of `Bug report`. A keyword list can't generalize to
paraphrases - this is exactly the gap a few-shot LLM classifier is expected to close.

**Praise and complaint keywords fire on the wrong clause of mixed messages.** `FB-0010`
("login page redesign looks a lot cleaner... nice work. still logs me out") is predicted
`Praise`/Positive because "nice work" matches before the bug clause is considered; the gold
label is `Bug report`/Mixed. The rule cascade checks bug keywords first, but "logs me out"
alone doesn't match the bug regex (no "crash/broken/bug/error" token), so praise wins by
default.

**Superficially similar wording, different intent is exactly where keyword matching breaks.**
`FB-0132` and `FB-0137` both mention login/access but are Questions ("does FlowHub support
SSO", "is there a support number"); the Service-complaint regex ("support (agent|team)?")
matches the word "support" used in an unrelated sense and overrides the question-mark rule,
mislabeling both as `Service complaint`. This is the taxonomy's documented ambiguous case
(similar wording, different meaning) and the baseline fails it as expected.

**Reversed bug-vs-complaint framing.** `FB-0029` (duplicate billing charge) and `FB-0062`
(unresolved calendar-sync bug, complained about) are gold-labeled `Service complaint` because
the customer's focus is on the billing/support handling, not the technical defect - but the
baseline's bug-keyword regex ("duplicate", "bug") fires first and predicts `Bug report`. This
distinction requires reading intent, which a keyword rule cannot do.

## Sentiment mistakes

Sentiment is the baseline's weakest field (27% accuracy, macro F1 0.20). VADER is tuned for
short, informal social-media text and consistently under-reacts to longer, matter-of-fact
support tickets:

- `FB-0009` ("Absolutely furious. I was locked out... for TWO DAYS... zero access.") scores
  compound **-0.16** - barely negative - and is predicted `Neutral` instead of `Negative`.
  "Furious" alone isn't enough to overcome the neutral tone of the surrounding factual
  sentences.
- `FB-0038` ("App crashes every single time...") scores compound **0.0** - VADER's lexicon
  has no entry for "crashes" in this technical sense, so a clearly negative bug report reads
  as completely neutral.
- `FB-0001` scores compound **+0.03** (barely positive territory) despite "driving my whole
  team crazy," because the rest of the sentence is descriptive rather than emotionally coded
  in VADER's lexicon.

This confirms a known limitation of lexicon-based sentiment: it reacts to emotionally-coded
words, not to negative *situations* described in neutral language. An LLM classifier with the
feedback's context (this is a support ticket about a blocking defect) should do meaningfully
better here.

## Ambiguous examples (as flagged in `gold_notes`)

- `FB-0004` ("logged out again??") - two characters of information, correctly flagged in
  `docs/taxonomy.md` as hard to classify confidently; baseline predicts `Question`/Neutral,
  gold is `Bug report`/Negative/Medium. A model with more context (or a longer feedback
  history from the same customer) would likely do better than either raw text alone.
- `FB-0063` vs. `FB-0066` - the "export" pair designed to test type disambiguation. Baseline
  correctly separates them by sentiment/urgency direction but predicts `Bug report` instead of
  the gold `Usability issue` for `FB-0063`, since "truncat-" matches the bug regex even though
  the taxonomy deliberately classifies this case as a usability issue (missing warning, not
  the defect itself).

## Low-confidence outputs

The baseline's confidence score is a simple function of how many keyword rules fired (0.5 base
+0.2 per matched rule, capped at 0.9). Records where **neither** the module nor type rule
matched score the baseline's floor (0.5) and are exactly the records most likely to be wrong:
`FB-0001`, `FB-0073`, `FB-0093`, `FB-0106`, `FB-0122` all scored 0.5 confidence and were all
misclassified on `feedback_type`. Low confidence is a reasonably good signal of low accuracy
for this baseline - a useful sanity check to carry into the LLM's self-reported `confidence`
field once real API runs are available.

## Where customer tier or rating influenced the result

- `FB-0023` (Enterprise, detailed performance complaint) is over-escalated to `High` urgency
  by the tier+sentiment rule (`Enterprise` + `Negative` → `High`), but gold is `Medium` -
  the rule doesn't account for the fact that a detailed, calm bug report from an Enterprise
  customer isn't automatically as urgent as an explicit "this is blocking us" statement.
- `FB-0038`/`FB-0044` (mobile crash, `rating=1`) are gold-labeled `High` urgency but the
  baseline predicts `Low`/`Medium` because the urgency rule only escalates on explicit
  urgency words or Enterprise tier - a 1-star rating on a crash report is a strong signal the
  rule currently ignores entirely.
- Low ratings (`rating=1`) correlate with gold `Negative` sentiment in every gold record that
  has one (`FB-0004`, `FB-0009`, `FB-0038`, `FB-0044`), but the baseline's sentiment detector
  never looks at `rating` at all - a clear, cheap improvement even without an LLM.

## Possible prompt / rule improvements

1. **Feed `rating` into both baseline urgency/sentiment rules and the LLM prompt explicitly**
   as a strong prior - a 1-2 star rating should raise the floor on negative sentiment and
   urgency regardless of text tone.
2. **For the LLM prompt**, add one explicit instruction addressing the taxonomy's own
   documented ambiguous cases (intent-over-keyword for Service complaint vs. Bug report;
   don't classify a mention of "support" as a Service complaint unless the complaint itself is
   about support/process).
3. **Expand the baseline's bug-keyword list** with phrasal patterns like "get(s)? logged out",
   "keeps happening", "won't (let|stop)" to reduce the Other-by-default failure mode - though
   this is fundamentally the ceiling of keyword matching, which is why the LLM classifier
   exists.
4. **Add a short few-shot example covering a Mixed-sentiment message** (e.g. praise + bug in
   one sentence) so the LLM sees the pattern explicitly rather than inferring it.
