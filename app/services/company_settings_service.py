from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_settings import CompanySettings
from app.schemas.company_settings import CompanySettingsUpsert

LOGO_UPLOAD_DIR = Path("app/static/company_logos")
MAX_LOGO_BYTES = 2 * 1024 * 1024
ALLOWED_LOGO_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


class InvalidLogoUploadError(ValueError):
    pass


def get_company_settings(db: Session, device_id: str) -> CompanySettings | None:
    statement = select(CompanySettings).where(CompanySettings.device_id == device_id)
    return db.scalar(statement)


def upsert_company_settings(
    db: Session,
    payload: CompanySettingsUpsert,
    device_id: str,
) -> CompanySettings:
    settings = get_company_settings(db, device_id)
    if settings is None:
        settings = CompanySettings(device_id=device_id)
        db.add(settings)

    update_data = payload.model_dump(exclude_unset=True)
    if "default_currency" in update_data and update_data["default_currency"]:
        update_data["default_currency"] = update_data["default_currency"].upper()

    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


def save_company_logo(
    db: Session,
    file: UploadFile,
    device_id: str,
) -> CompanySettings:
    extension = ALLOWED_LOGO_CONTENT_TYPES.get(file.content_type or "")
    if extension is None:
        raise InvalidLogoUploadError("Logo must be PNG, JPG, WEBP, or SVG")

    content = file.file.read(MAX_LOGO_BYTES + 1)
    if not content:
        raise InvalidLogoUploadError("Logo file is required")
    if len(content) > MAX_LOGO_BYTES:
        raise InvalidLogoUploadError("Logo file must be 2MB or smaller")

    LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{device_id}-{uuid4().hex}{extension}"
    logo_path = LOGO_UPLOAD_DIR / filename
    logo_path.write_bytes(content)

    settings = get_company_settings(db, device_id)
    if settings is None:
        settings = CompanySettings(device_id=device_id)
        db.add(settings)

    settings.logo_url = f"/static/company_logos/{filename}"
    db.commit()
    db.refresh(settings)
    return settings
