"""Thin CSV loading helpers shared by the classification pipeline."""

import csv
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts: str) -> str:
    return os.path.join(REPO_ROOT, *parts)


def read_csv(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_full_dataset() -> list[dict]:
    """All 150 records (data/processed/feedback_dataset.csv), all columns including labels."""
    return read_csv(_path("data", "processed", "feedback_dataset.csv"))


def load_non_gold_records() -> list[dict]:
    """The 120 non-gold records - the only pool few-shot examples may be drawn from."""
    return [r for r in load_full_dataset() if r["is_gold_label"] != "True"]


def load_gold_records() -> list[dict]:
    """The 30 gold records (data/evaluation/gold_feedback.csv), all columns including labels."""
    return read_csv(_path("data", "evaluation", "gold_feedback.csv"))
