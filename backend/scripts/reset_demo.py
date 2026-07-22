"""Reset the shared "demo" workspace and reseed it from the canonical synthetic
dataset (backend/data/processed/feedback_dataset.csv).

Wipes only workspace_id="demo" - other workspaces (anonymous browser sessions,
e2e test runs) are untouched. Reseeding runs the free, local pipeline only
(cached embeddings, baseline rule-based classifier, deterministic theme
clustering) - no LLM calls, no cost.

Run scripts/data/generate_dataset.py first if you want fresh dates (it rescales
feedback timestamps into a rolling 4-week window ending today - see WINDOW_DAYS
there), then run this to push the regenerated CSV into Postgres:

    python3 scripts/data/generate_dataset.py
    python3 scripts/reset_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.analysis import AnalysisResult  # noqa: E402
from app.models.context import ContextMatch  # noqa: E402
from app.models.embedding import Embedding  # noqa: E402
from app.models.feedback import Feedback  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.theme import Theme, ThemeMember  # noqa: E402
from app.schemas.analysis import BatchAnalysisRequest  # noqa: E402
from app.schemas.feedback import ImportSummary  # noqa: E402
from app.services import analysis_service, theme_service  # noqa: E402
from app.services.import_service import _import_context_matches, _import_embeddings, _import_feedback  # noqa: E402

WORKSPACE_ID = "demo"


def _wipe_workspace(db) -> int:
    feedback_ids = select(Feedback.id).where(Feedback.workspace_id == WORKSPACE_ID)
    theme_ids = select(Theme.id).where(Theme.workspace_id == WORKSPACE_ID)

    db.execute(delete(ContextMatch).where(ContextMatch.feedback_id.in_(feedback_ids)))
    db.execute(delete(ThemeMember).where(
        ThemeMember.feedback_id.in_(feedback_ids) | ThemeMember.theme_id.in_(theme_ids)
    ))
    db.execute(delete(Embedding).where(Embedding.feedback_id.in_(feedback_ids)))
    db.execute(delete(AnalysisResult).where(AnalysisResult.feedback_id.in_(feedback_ids)))
    db.execute(delete(Theme).where(Theme.workspace_id == WORKSPACE_ID))
    db.execute(delete(Report).where(Report.workspace_id == WORKSPACE_ID))
    result = db.execute(delete(Feedback).where(Feedback.workspace_id == WORKSPACE_ID))
    db.flush()
    return result.rowcount


def main():
    db = SessionLocal()
    try:
        deleted = _wipe_workspace(db)
        print(f"Deleted {deleted} feedback rows (with cascaded analysis/embeddings/themes/reports) "
              f"from workspace '{WORKSPACE_ID}'.")

        summary = ImportSummary()
        _import_feedback(db, summary)
        db.flush()
        _import_embeddings(db, summary)
        _import_context_matches(db, summary)
        db.flush()
        print(f"Reimported {summary.feedback_imported} feedback, {summary.embeddings_imported} embeddings, "
              f"{summary.context_matches_imported} context matches.")

        batch_result = analysis_service.run_batch(db, BatchAnalysisRequest(method="baseline"), workspace_id=WORKSPACE_ID)
        succeeded = sum(1 for r in batch_result if r.status == "success")
        print(f"Classified {succeeded}/{len(batch_result)} feedback records (local baseline classifier, no LLM).")

        theme_result = theme_service.recompute_themes(db, workspace_id=WORKSPACE_ID)
        print(f"Recomputed themes: {theme_result.themes_created} themes, "
              f"{theme_result.feedback_assigned} feedback assigned, {theme_result.feedback_unclustered} unclustered.")

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Demo workspace reset complete.")


if __name__ == "__main__":
    main()
