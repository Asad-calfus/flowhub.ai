"""Evaluate a stored weekly report against the evidence pack it was generated from.

Usage:
    python3 scripts/pipeline/evaluate_weekly_report.py                  # evaluates the most recent report
    python3 scripts/pipeline/evaluate_weekly_report.py --report-id RPT-0001
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.report import Report  # noqa: E402
from src.reports.evaluator import evaluate_report  # noqa: E402
from src.reports.schemas import EvidencePack, WeeklyReport  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results", "reports")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-id", default=None, help="report id to evaluate; defaults to the most recent")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.report_id:
            row = db.get(Report, args.report_id)
        else:
            row = db.execute(select(Report).order_by(Report.created_at.desc()).limit(1)).scalars().first()
    finally:
        db.close()

    if row is None:
        print("No report found to evaluate. Generate one first with generate_weekly_report.py.")
        sys.exit(1)

    report = WeeklyReport(**row.report_json)
    pack = EvidencePack(**row.evidence_json)
    evaluation = evaluate_report(report, pack)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "report_evaluation.json")
    payload = {"report_id": row.id, **evaluation.to_dict()}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Evaluated report {row.id}")
    for key, value in payload.items():
        print(f"  {key}: {value}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
