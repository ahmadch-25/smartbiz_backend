from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_device_id
from app.schemas.api_response import ApiResponse
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardSummaryResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    summary = dashboard_service.get_dashboard_summary(db, device_id)
    return ApiResponse(status=True, message="success", result=summary)
