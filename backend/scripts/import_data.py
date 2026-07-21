"""One-time backfill of existing dataset/pipeline outputs into Postgres.

Safe to run multiple times - every insert is guarded by an existence check, so re-running
only reports skips for anything already imported. Does not call any LLM.

Usage:
    python3 scripts/import_data.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.services.import_service import run_full_import  # noqa: E402


def main():
    db = SessionLocal()
    try:
        summary = run_full_import(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Import summary:")
    for field, value in summary.model_dump().items():
        if field == "errors":
            continue
        print(f"  {field}: {value}")
    if summary.errors:
        print(f"  errors ({len(summary.errors)}):")
        for err in summary.errors:
            print(f"    - {err}")


if __name__ == "__main__":
    main()
