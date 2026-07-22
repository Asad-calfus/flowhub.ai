from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.workspace import get_workspace_id
from app.schemas.copilot import CopilotAnswerOut, CopilotAskRequest
from app.services import copilot_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/ask", response_model=CopilotAnswerOut)
def ask(payload: CopilotAskRequest, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)) -> CopilotAnswerOut:
    return copilot_service.ask(db, payload, workspace_id)
