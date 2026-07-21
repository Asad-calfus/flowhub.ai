# Retrieval Error Analysis — Phase 3

Based on `results/retrieval/context_match_predictions.csv` and `similar_feedback_predictions.csv`
against the 30 gold records. Model: `sentence-transformers/all-MiniLM-L6-v2`.

## Correct matches

Context matching is strong overall: **recall@3 = 1.0**, **MRR = 0.90**, **recall@1 = 0.83**
across the 24 gold records with a known bug/feature-request match. All 24 true matches
appear somewhere in the top-3 candidates.

## Missed rank-1 (recovered by rank-3)

Four records: the correct bug ranked 2nd-3rd, not 1st.

- `FB-0004`, `FB-0006`, `FB-0010` (all short/ambiguous "logged out" phrasing) rank
  **BUG-012** (mobile random logout) above the true **BUG-001** (SSO session expiry). Both
  bugs share near-identical vocabulary ("logged out"); nothing in the allowed input fields
  (no module tag) disambiguates SSO-specific vs. mobile-specific logout.
- `FB-0019` (the German-language gold record) ranks a feature request above the true
  **BUG-002**. `all-MiniLM-L6-v2` is primarily English-trained; non-English text embeds less
  reliably - expected given the model choice, not a logic bug.

## False known-issue rate (new issues incorrectly matched)

2 of 6 gold "new issue" records (33%) were matched to an existing bug/feature request:

- `FB-0093` (new feature request: custom fields) → matched **FR-002** (bulk task editing) at
  0.53 - both are Task Management feature requests using similar generic phrasing ("select
  multiple", "workflows"). A real duplicate-detector would need finer-grained text, not just
  module + topic overlap.
- `FB-0122` (new performance issue: slow report generation) → labeled `possible_release_issue`
  against v2.6.0 at 0.34 - just above `LOW_SIGNAL_THRESHOLD` (0.35 is the cutoff, this scored
  0.36 on the bug side, release scored comparably). A borderline case, not a confident wrong
  match.

## Status vs. rank-1 bug: a labeling nuance

`FB-0014`'s true bug (`BUG-002`) is correctly ranked #1 among bugs+feature-requests (0.61),
but the final `status` is `possible_release_issue` because a *release* record scored higher
still. Releases compete in the same status-ranking as bugs/features despite there being only
6 of them with broad, general text - they can out-score a correct bug match without being
"wrong" in the recall@k sense (which only pools bugs+features). Worth a threshold-per-type
approach in a future pass rather than one global ranked pool.

## Similar-wording-different-meaning check

`FB-0063` (usability/bug: CSV export truncation) and `FB-0066` (feature request: Excel
formatting) - designed to share "export" vocabulary but differ in intent:

- `FB-0066` retrieves `FB-0063` in its top-5 (mild false positive - topically close, but a
  bug report and a feature request being neighbors isn't necessarily wrong for *semantic*
  similarity, just not useful for *duplicate-type* disambiguation).
- `FB-0063` does **not** retrieve `FB-0066` back - asymmetric, expected with cosine top-k
  (neighborhoods aren't symmetric when other records compete for the top slots).

## Same-theme retrieval (similar-feedback search, all 150 records)

**Same-theme precision@5 = recall@5 = 0.66** across the 69 themed records. Reasonable for a
generic sentence embedding with no fine-tuning on this domain; misses are concentrated in
themes with more lexical variety (e.g. "Confusing billing charges" spans complaints,
questions, and bug reports with little shared vocabulary beyond "billing"/"charge").

## Version-related failures

No systematic version-based failures observed - `product_version` is included in the
embedding text but the model has no special handling for it (it's just a token), so it
nudges similarity slightly rather than hard-filtering. Not a concern at this dataset size.

## Threshold recommendations

- `CONTEXT_MATCH_THRESHOLD=0.5` / `CONTEXT_LOW_SIGNAL_THRESHOLD=0.35` (current defaults)
  produce recall@3=1.0 with a modest 33% false-known-issue rate on new issues - reasonable for
  a v1, but the false-known-issue rate suggests raising `MATCH_THRESHOLD` slightly (e.g. 0.55)
  would trade a little recall@1 for fewer false positives on genuinely new issues. Not changed
  in this phase - flagged for tuning once more data exists.

## Dataset limitations affecting retrieval

- 15 bugs / 12 feature requests is a small candidate pool - some false positives (`FB-0093`)
  are a direct result of few candidates competing for the top slot.
- Only 1 non-English gold record - not enough to characterize multilingual performance beyond
  "notably weaker," as seen with `FB-0019`.
