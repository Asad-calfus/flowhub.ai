from fastapi import APIRouter

from app.api.routes import analysis, churn, copilot, feedback, health, reports, themes

api_router = APIRouter()
api_router.include_router(health.v1_router)
api_router.include_router(feedback.router)
api_router.include_router(analysis.router)
api_router.include_router(themes.router)
api_router.include_router(reports.router)
api_router.include_router(churn.router)
api_router.include_router(copilot.router)
