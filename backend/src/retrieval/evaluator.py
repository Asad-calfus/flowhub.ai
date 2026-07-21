"""Retrieval evaluation metrics. `related_context_id`/`theme_hint` are read here only -
after retrieval has already run - purely as ground truth to score against.
"""

from statistics import mean

# Documented ambiguous pairs from data/evaluation/gold_feedback.csv gold_notes, used to spot
# check retrieval on the dataset's known "similar wording, different meaning" cases.
SIMILAR_WORDING_DIFFERENT_MEANING_PAIRS = [("FB-0063", "FB-0066")]


def _rank_of(true_id: str, candidates: list) -> int | None:
    ranked = sorted(candidates, key=lambda c: -c.similarity_score)
    for i, c in enumerate(ranked):
        if c.context_id == true_id:
            return i + 1
    return None


def evaluate_context_matches(gold_rows: list[dict], results: dict) -> dict:
    with_ctx = [r for r in gold_rows if r["related_context_id"]]
    without_ctx = [r for r in gold_rows if not r["related_context_id"]]

    recall1 = recall3 = precision1 = rr_sum = 0
    n = 0
    for r in with_ctx:
        res = results.get(r["feedback_id"])
        if res is None:
            continue
        n += 1
        rank = _rank_of(r["related_context_id"], res.bugs + res.feature_requests)
        if rank == 1:
            recall1 += 1
            precision1 += 1
        if rank is not None and rank <= 3:
            recall3 += 1
        if rank is not None:
            rr_sum += 1.0 / rank

    type_correct = type_n = 0
    for r in with_ctx:
        res = results.get(r["feedback_id"])
        if res is None:
            continue
        type_n += 1
        expected = "known_bug" if r["related_context_id"].startswith("BUG") else "duplicate_feature_request"
        type_correct += res.status == expected

    def _rate(pred_fn):
        vals = [results[r["feedback_id"]] for r in without_ctx if r["feedback_id"] in results]
        return sum(1 for v in vals if pred_fn(v)) / len(vals) if vals else None

    return {
        "n_with_context": n,
        "recall_at_1": recall1 / n if n else None,
        "recall_at_3": recall3 / n if n else None,
        "precision_at_1": precision1 / n if n else None,
        "mrr": rr_sum / n if n else None,
        "context_type_accuracy": type_correct / type_n if type_n else None,
        "n_without_context": len(without_ctx),
        "new_issue_detection_accuracy": _rate(lambda v: v.status == "new_untracked_issue"),
        "no_confident_match_rate": _rate(lambda v: v.status == "no_confident_match"),
        "false_known_issue_rate": _rate(
            lambda v: v.status in ("known_bug", "duplicate_feature_request", "possible_release_issue")
        ),
    }


def evaluate_similar_feedback(all_rows: list[dict], top5_by_id: dict[str, list[tuple[str, float]]]) -> dict:
    theme_by_id = {r["feedback_id"]: r["theme_hint"] for r in all_rows}
    theme_members: dict[str, set] = {}
    for r in all_rows:
        if r["theme_hint"]:
            theme_members.setdefault(r["theme_hint"], set()).add(r["feedback_id"])

    precisions, recalls = [], []
    for r in all_rows:
        if not r["theme_hint"]:
            continue
        fid, theme = r["feedback_id"], r["theme_hint"]
        others = theme_members[theme] - {fid}
        if not others or fid not in top5_by_id:
            continue
        top5_ids = [mid for mid, _ in top5_by_id[fid]]
        hits = sum(1 for mid in top5_ids if theme_by_id.get(mid) == theme)
        precisions.append(hits / len(top5_ids) if top5_ids else 0.0)
        recalls.append(hits / min(len(others), 5))

    pair_results = []
    for a, b in SIMILAR_WORDING_DIFFERENT_MEANING_PAIRS:
        a_top = {mid for mid, _ in top5_by_id.get(a, [])}
        b_top = {mid for mid, _ in top5_by_id.get(b, [])}
        pair_results.append({
            "pair": [a, b],
            "a_retrieved_b": b in a_top,
            "b_retrieved_a": a in b_top,
        })

    return {
        "same_theme_precision_at_5": mean(precisions) if precisions else None,
        "same_theme_recall_at_5": mean(recalls) if recalls else None,
        "n_themed_records_evaluated": len(precisions),
        "similar_wording_different_meaning_checks": pair_results,
    }
