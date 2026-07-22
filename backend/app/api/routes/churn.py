from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.workspace import get_workspace_id
from app.schemas.churn import CustomerRiskOut
from app.services import churn_service

router = APIRouter(prefix="/churn", tags=["churn"])


@router.get("/customers", response_model=list[CustomerRiskOut])
def list_at_risk_customers(
    db: Session = Depends(get_db),
    workspace_id: str = Depends(get_workspace_id),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[CustomerRiskOut]:
    scores = churn_service.list_at_risk_customers(db, workspace_id, limit)
    return [CustomerRiskOut.model_validate(s) for s in scores]


@router.get("/customers/{customer_id}", response_model=CustomerRiskOut)
def get_customer_risk(customer_id: str, db: Session = Depends(get_db), workspace_id: str = Depends(get_workspace_id)) -> CustomerRiskOut:
    score = churn_service.get_customer_risk(db, customer_id, workspace_id)
    if score is None:
        raise NotFoundError("Customer", customer_id)
    return CustomerRiskOut.model_validate(score, from_attributes=True)
