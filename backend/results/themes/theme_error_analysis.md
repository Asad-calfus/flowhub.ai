# Theme Clustering Error Analysis — Phase 4

Based on `results/themes/theme_assignments.csv`, `themes.csv`, and `theme_metrics.json`
(`evaluation` section) against the 8 documented recurring `theme_hint` values (69 of 150
records). Clustering config: `AgglomerativeClustering` (cosine distance, average linkage),
`THEME_DISTANCE_THRESHOLD=0.55`, `THEME_MIN_SIZE=4`.

## Strong themes

Several predicted clusters map cleanly onto a single `theme_hint` with no mixing:

- `THM-002` (Dashboard load slow seconds, 8/8 "Slow dashboard loading")
- `THM-003` (Dashboard dark mode theme eyes, 7/7 "Missing dark mode")
- `THM-008` (Notifications instant push delayed, 5/5 "Delayed notifications")
- `THM-010` (Mobile App opening android attachments crashes, 5/5 "Mobile app crashes")
- `THM-006` (Authentication email password reset support, all password-reset wording)

Overall cluster purity (majority-label fraction, weighted) is **0.92** and pairwise
precision is **0.85** - when the clusterer does group two themed records together, it is
usually right.

## Fragmented themes

Three true themes split across two predicted clusters each (`n_fragmented_true_themes=3`
in the evaluation section):

- **"Login failures after an update"**: `THM-001` (5 members) and `THM-011` (2 members).
  `THM-011` is specifically the SSO/Okta-worded subset ("sso", "okta", "session" as top
  keywords); `THM-001` is the more generic "logged out" wording. Same fine-grained
  vocabulary split noted in Phase 3's retrieval error analysis (`BUG-012` vs `BUG-001`
  confusion on `FB-0004`/`FB-0006`/`FB-0010`) - the embedding model separates specific SSO
  terminology from generic logout complaints even within the same true theme.
- **"Confusing billing charges"**: `THM-004` (2 members) and `THM-009` (3 members).
  `THM-009` clusters around "invoice"/"tax" wording; `THM-004` around "enterprise"/"pro"/
  "price" (plan-tier) wording. Genuinely two different billing complaint angles that share
  a `theme_hint` but not vocabulary.
- **"Mobile app crashes"**: fully absorbed into `THM-001` (3 members) rather than forming
  its own cluster - see "incorrectly merged" below.

## Incorrectly merged themes

`THM-001` mixes 5 "Login failures after an update" records with 3 "Mobile app crashes"
records. Both share "logged out"/"crashes"/"app" vocabulary at the sentence level even
though the underlying issues (SSO session expiry vs. mobile app stability) are unrelated -
the same ambiguity Phase 3 flagged for retrieval (`FB-0004`, `FB-0006`, `FB-0010` ranking
`BUG-012` mobile-logout above the true `BUG-001` SSO bug). No other predicted cluster mixes
true themes below a 50% majority (`n_mixed_predicted_themes=0`), so this is the one clear
merge error at the current threshold.

## Unclustered useful feedback

66 of 150 records (44%) are unclustered; 17 of those have a `theme_hint`, i.e. genuinely
belong to one of the 8 recurring themes but didn't form/join a size-≥4 cluster:

- **"Integration synchronization failures"** is the worst-affected true theme: only 3 of
  its 8 members made it into a theme (`THM-012`, alongside one non-hinted record); the
  other 5 (`FB-0057`, `FB-0058`, `FB-0059`, `FB-0060`, `FB-0062`) stayed unclustered -
  integration complaints apparently use more varied vocabulary (different third-party tool
  names) than the other themes.
- **"Difficulty exporting reports"**: `FB-0066` and `FB-0067` stayed unclustered while
  `FB-0063` joined `THM-005`; export complaints split between "CSV row limit" and
  "Excel formatting" framings (see the near-duplicate case below).
- **"Confusing billing charges"** and **"Delayed notifications"** each lost several members
  to the unclustered pool the same way - real themes with above-average internal wording
  diversity are the ones `MIN_THEME_SIZE=4` and `DISTANCE_THRESHOLD=0.55` filter out most
  aggressively.

This is the expected, documented trade-off of not forcing every record into a theme -
raising `THEME_DISTANCE_THRESHOLD` recovers some of these (see "Recommended threshold
changes" below) at the cost of more merge errors like `THM-001` above.

## Similar-wording-different-meaning check

`FB-0063` ("CSV export silently drops rows past 1000") and `FB-0066` ("want Excel export
with real formatting") - the same pair flagged in Phase 3's retrieval analysis for sharing
"export" vocabulary with different intent. Both actually carry the *same* `theme_hint`
("Difficulty exporting reports") here, but only `FB-0063` clustered (into `THM-005`);
`FB-0066` stayed unclustered rather than being incorrectly merged elsewhere - a safe
outcome, though it undercounts the theme's true size.

## Non-English clustering behavior

All 5 non-English gold-adjacent records (`FB-0019` de, `FB-0099` es, `FB-0124` fr,
`FB-0138` pt, `FB-0146` es) are unclustered, including `FB-0019` which does carry a
`theme_hint` ("Delayed notifications"). Consistent with Phase 3's finding that
`all-MiniLM-L6-v2` is primarily English-trained - non-English text embeds farther from its
same-theme English neighbors than the distance threshold allows. Not something to fix by
threshold tuning; would need a multilingual embedding model.

## Recommended threshold changes

Grid search over `THEME_DISTANCE_THRESHOLD` (0.4-0.85) against ARI/NMI showed scores
climbing continuously up to ~0.72 (ARI 0.70, NMI 0.83) before collapsing past 0.75 as
everything merges into 1-2 giant clusters. The 0.72 setting was **not** adopted: it produces
a 32-member top cluster (vs. a real max theme size of 10), i.e. several unrelated true
themes glommed into one blob - a worse failure mode (per this phase's explicit "avoid
incorrectly merged themes" requirement) than the coverage lost at a stricter threshold.
`0.55`/`min_size=4` was chosen instead because inspecting cluster composition directly
(not just the aggregate metric) showed cluster sizes staying close to real theme sizes
(4-8) with only the one `THM-001` merge error, at the cost of 44% unclustered. A future
pass could try per-theme adaptive thresholds instead of one global cutoff, given how much
the fragmentation/coverage trade-off varies theme by theme (Integrations vs. Dashboard).

## Dataset limitations

- Only 69 of 150 records carry a `theme_hint` at all; the other 81 have no ground truth to
  evaluate against, so precision/recall/ARI/NMI are computed on under half the dataset.
- 8 recurring themes with 5-10 gold-hinted members each is a small sample per theme -
  individual vocabulary quirks (e.g. "invoice/tax" vs. "enterprise/pro" within "Confusing
  billing charges") have an outsized effect on fragmentation counts at this scale.
- Same non-English sample-size limitation as Phase 3 (1-5 records per language, not enough
  to characterize multilingual clustering beyond "notably weaker").
