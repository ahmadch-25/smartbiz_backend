from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_device_id
from app.schemas.api_response import ApiResponse
from app.schemas.company_settings import (
    CompanySettingsResponse,
    CompanySettingsUpsert,
)
from app.services import company_settings_service

router = APIRouter(prefix="/company-settings", tags=["Company Settings"])


@router.get("", response_model=CompanySettingsResponse)
def get_company_settings(
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    settings = company_settings_service.get_company_settings(db, device_id)
    return ApiResponse(status=True, message="success", result=settings)


@router.put("", response_model=CompanySettingsResponse)
def upsert_company_settings(
    payload: CompanySettingsUpsert,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    settings = company_settings_service.upsert_company_settings(db, payload, device_id)
    return ApiResponse(status=True, message="success", result=settings)


@router.post("/logo", response_model=CompanySettingsResponse)
def upload_company_logo(
    logo: UploadFile,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    try:
        settings = company_settings_service.save_company_logo(db, logo, device_id)
    except company_settings_service.InvalidLogoUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ApiResponse(status=True, message="success", result=settings)
