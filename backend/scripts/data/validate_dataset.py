"""
Lightweight validation for the Phase 1 synthetic feedback dataset.

Run:
    python3 scripts/data/validate_dataset.py

Performs structural and referential checks on data/processed/feedback_dataset.csv,
data/evaluation/gold_feedback.csv, and the data/context/*.csv files. Prints a
clear PASS/FAIL report and exits with a non-zero status if any check fails.
"""

import csv
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def path(*parts):
    return os.path.join(BASE_DIR, *parts)


def read_csv(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


EXPECTED_FEEDBACK_COUNT = 150
EXPECTED_GOLD_COUNT = 30
EXPECTED_MODULE_COUNT = 8
EXPECTED_BUG_COUNT = 15
EXPECTED_FR_COUNT = 12
EXPECTED_RELEASE_COUNT = 6

VALID_TIERS = {"Free", "Pro", "Enterprise"}
VALID_SOURCES = {"Support ticket", "Survey", "App review", "Chat", "Email", "Community post"}
VALID_TYPES = {"Bug report", "Feature request", "Usability issue", "Performance issue",
               "Service complaint", "Praise", "Question", "Other"}
VALID_SENTIMENTS = {"Positive", "Neutral", "Negative", "Mixed"}
VALID_URGENCY = {"Low", "Medium", "High"}
VALID_LABEL_SOURCES = {"Synthetic", "Manually verified"}
VALID_BOOL = {"True", "False"}


def check(results, name, passed, detail=""):
    results.append((name, passed, detail))


def is_valid_timestamp(value):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def main():
    results = []

    feedback = read_csv(path("data", "processed", "feedback_dataset.csv"))
    gold = read_csv(path("data", "evaluation", "gold_feedback.csv"))
    modules = read_csv(path("data", "context", "product_modules.csv"))
    bugs = read_csv(path("data", "context", "known_bugs.csv"))
    frs = read_csv(path("data", "context", "feature_requests.csv"))
    releases = read_csv(path("data", "context", "product_releases.csv"))

    module_names = {m["module_name"] for m in modules}
    bug_ids = {b["bug_id"] for b in bugs}
    fr_ids = {f["request_id"] for f in frs}

    # 1. Correct number of records
    check(results, "Correct number of feedback records (150)",
          len(feedback) == EXPECTED_FEEDBACK_COUNT, f"found {len(feedback)}")
    check(results, "Correct number of gold records (30)",
          len(gold) == EXPECTED_GOLD_COUNT, f"found {len(gold)}")
    check(results, "Correct number of product modules (8)",
          len(modules) == EXPECTED_MODULE_COUNT, f"found {len(modules)}")
    check(results, "Correct number of known bugs (15)",
          len(bugs) == EXPECTED_BUG_COUNT, f"found {len(bugs)}")
    check(results, "Correct number of feature requests (12)",
          len(frs) == EXPECTED_FR_COUNT, f"found {len(frs)}")
    check(results, "Correct number of product releases (6)",
          len(releases) == EXPECTED_RELEASE_COUNT, f"found {len(releases)}")

    # 2. Unique feedback IDs
    ids = [r["feedback_id"] for r in feedback]
    check(results, "Unique feedback IDs", len(ids) == len(set(ids)),
          f"{len(ids) - len(set(ids))} duplicate IDs")

    # 3. Non-empty feedback text
    empty_text = [r["feedback_id"] for r in feedback if not r["feedback_text"].strip()]
    check(results, "Non-empty feedback text", len(empty_text) == 0,
          f"empty text in: {empty_text}")

    # 4. Valid timestamps
    bad_ts = [r["feedback_id"] for r in feedback if not is_valid_timestamp(r["created_at"])]
    check(results, "Valid timestamps", len(bad_ts) == 0, f"invalid timestamps in: {bad_ts}")

    # 5. Approved label values (type, sentiment, urgency, label_source, is_gold_label)
    bad_type = [r["feedback_id"] for r in feedback if r["feedback_type"] not in VALID_TYPES]
    check(results, "Valid feedback_type values", len(bad_type) == 0, f"bad values in: {bad_type}")

    bad_sent = [r["feedback_id"] for r in feedback if r["sentiment"] not in VALID_SENTIMENTS]
    check(results, "Valid sentiment values", len(bad_sent) == 0, f"bad values in: {bad_sent}")

    bad_urg = [r["feedback_id"] for r in feedback if r["urgency"] not in VALID_URGENCY]
    check(results, "Valid urgency values", len(bad_urg) == 0, f"bad values in: {bad_urg}")

    bad_label_src = [r["feedback_id"] for r in feedback if r["label_source"] not in VALID_LABEL_SOURCES]
    check(results, "Valid label_source values", len(bad_label_src) == 0, f"bad values in: {bad_label_src}")

    bad_gold_flag = [r["feedback_id"] for r in feedback if r["is_gold_label"] not in VALID_BOOL]
    check(results, "Valid is_gold_label values", len(bad_gold_flag) == 0, f"bad values in: {bad_gold_flag}")

    bad_source = [r["feedback_id"] for r in feedback if r["source"] not in VALID_SOURCES]
    check(results, "Valid source values", len(bad_source) == 0, f"bad values in: {bad_source}")

    # 6. Valid customer tiers
    bad_tier = [r["feedback_id"] for r in feedback if r["customer_tier"] not in VALID_TIERS]
    check(results, "Valid customer_tier values", len(bad_tier) == 0, f"bad values in: {bad_tier}")

    # 7. Valid product modules
    bad_module = [r["feedback_id"] for r in feedback if r["product_module"] not in module_names]
    check(results, "Valid product_module values", len(bad_module) == 0, f"bad values in: {bad_module}")

    # 8. Rating range (1-5 or blank)
    bad_rating = []
    for r in feedback:
        val = r["rating"].strip()
        if val == "":
            continue
        if not val.isdigit() or not (1 <= int(val) <= 5):
            bad_rating.append(r["feedback_id"])
    check(results, "Rating within 1-5 range (or blank)", len(bad_rating) == 0, f"bad values in: {bad_rating}")

    # 9. Missing required fields (all except rating, product_version, theme_hint, related_context_id)
    required_fields = ["feedback_id", "feedback_text", "source", "created_at", "customer_id",
                        "customer_tier", "product_module", "language", "feedback_type",
                        "category", "sentiment", "urgency", "is_gold_label", "label_source"]
    missing = []
    for r in feedback:
        for field in required_fields:
            if not r.get(field, "").strip():
                missing.append((r["feedback_id"], field))
    check(results, "No missing required fields", len(missing) == 0, f"missing: {missing}")

    # 10. Duplicate feedback text (exact duplicates should not exist)
    texts = [r["feedback_text"].strip() for r in feedback]
    seen, dupes = set(), []
    for t in texts:
        if t in seen:
            dupes.append(t)
        seen.add(t)
    check(results, "No exact duplicate feedback text", len(dupes) == 0, f"{len(dupes)} exact duplicates")

    # 11. Invalid context references (related_context_id must exist in bugs or feature requests, or be blank)
    bad_context = []
    for r in feedback:
        ctx = r["related_context_id"].strip()
        if ctx and ctx not in bug_ids and ctx not in fr_ids:
            bad_context.append((r["feedback_id"], ctx))
    check(results, "All related_context_id values reference a real bug/feature request",
          len(bad_context) == 0, f"invalid refs: {bad_context}")

    # 12. Gold records exist in the main dataset
    main_ids = {r["feedback_id"] for r in feedback}
    gold_ids = {r["feedback_id"] for r in gold}
    missing_gold = gold_ids - main_ids
    check(results, "All gold records exist in the main dataset", len(missing_gold) == 0,
          f"missing: {missing_gold}")

    # 13. Gold records correctly flagged in main dataset
    flagged_gold = {r["feedback_id"] for r in feedback if r["is_gold_label"] == "True"}
    check(results, "is_gold_label flag matches gold evaluation set", flagged_gold == gold_ids,
          f"mismatch: {flagged_gold.symmetric_difference(gold_ids)}")

    # --- Print report ---
    print("=" * 70)
    print("DATASET VALIDATION REPORT")
    print("=" * 70)
    passed_count = 0
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        line = f"[{status}] {name}"
        if not passed and detail:
            line += f" -> {detail}"
        print(line)
        if passed:
            passed_count += 1
    print("-" * 70)
    print(f"{passed_count}/{len(results)} checks passed")
    print("=" * 70)

    if passed_count != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
