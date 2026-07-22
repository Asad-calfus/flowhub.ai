"""Generate a weekly customer-feedback report over stored (Postgres) data.

Safe by default: always dry-run (no API calls, no cost) unless you pass --live
explicitly, even if an API key is present in the environment.

Usage:
    python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-01 --end 2026-05-07
        # deterministic, template-based report - no LLM involved at all

    python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-01 --end 2026-05-07 --mode dry-run
        # exercises the LLM narrative path with a deterministic local stub - no API calls

    python3 scripts/pipeline/generate_weekly_report.py --start 2026-05-01 --end 2026-05-07 --mode live
        # real API call; prints a rough cost estimate and asks for confirmation first

    python3 scripts/pipeline/generate_weekly_report.py --start ... --end ... --mode live --yes --force
    python3 scripts/pipeline/generate_weekly_report.py --start ... --end ... --module Dashboard --tier Enterprise

    python3 scripts/pipeline/generate_weekly_report.py
        # omit --start/--end for an all-time report over every stored feedback record
        # (including records with no feedback_created_at) - no period-over-period trend
"""

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal  # noqa: E402
from app.schemas.report import ReportGenerationRequest  # noqa: E402
from app.services import report_service  # noqa: E402
from src.classification.pricing import RECOMMENDED_MODEL, estimate_cost_usd  # noqa: E402
from src.reports import generator  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results", "reports")


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _confirm_live_run(llm: "generator.LLMReportGenerator") -> bool:
    estimate = estimate_cost_usd(llm.model, input_tokens=3000, output_tokens=800)
    print(f"About to make 1 real '{llm.provider}' API call with model '{llm.model}'.")
    if estimate is not None:
        print(f"Estimated cost: ~${estimate:.4f} USD (rough estimate, not billing-accurate).")
    else:
        print(f"No pricing data for model '{llm.model}' - cost estimate unavailable.")
        print(f"Cost-efficient defaults: {RECOMMENDED_MODEL}")
    reply = input("Proceed with live API call? [y/N]: ").strip().lower()
    return reply == "y"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=None, help="period start date, YYYY-MM-DD (omit both --start/--end for all-time)")
    parser.add_argument("--end", default=None, help="period end date, YYYY-MM-DD, inclusive (omit both --start/--end for all-time)")
    parser.add_argument("--mode", choices=["deterministic", "dry-run", "live"], default="deterministic")
    parser.add_argument("--module", default=None, help="optional product_module filter")
    parser.add_argument("--tier", default=None, help="optional customer_tier filter")
    parser.add_argument("--force", action="store_true", help="bypass the LLM narrative cache")
    parser.add_argument("--yes", action="store_true", help="skip the cost-estimate confirmation prompt for --mode live")
    args = parser.parse_args()

    if bool(args.start) != bool(args.end):
        print("--start and --end must both be given, or both omitted for an all-time report.")
        sys.exit(1)

    mode = {"deterministic": "deterministic", "dry-run": "dry_run", "live": "live"}[args.mode]
    request = ReportGenerationRequest(
        start_date=_parse_date(args.start) if args.start else None,
        end_date=_parse_date(args.end) if args.end else None,
        mode=mode,
        product_module=args.module,
        customer_tier=args.tier,
        force=args.force,
    )

    if mode == "live" and not args.yes:
        llm = generator.LLMReportGenerator(dry_run=False)
        if not llm.api_key:
            print(f"--mode live requires {llm._api_key_env_var()} to be set. Aborting.")
            sys.exit(1)
        if not _confirm_live_run(llm):
            print("Aborted - no API call made.")
            sys.exit(0)

    db = SessionLocal()
    try:
        report = report_service.generate_report(db, request)
        db.commit()
        report_id, method, model_name = report.id, report.generation_method, report.model_name
        start_date, end_date = report.start_date, report.end_date
        report_json, markdown = report.report_json, report.markdown
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    json_path = os.path.join(RESULTS_DIR, "weekly_report.json")
    md_path = os.path.join(RESULTS_DIR, "weekly_report.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Generated report {report_id} ({method}, model={model_name})")
    print(f"Period: {start_date} to {end_date}")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
