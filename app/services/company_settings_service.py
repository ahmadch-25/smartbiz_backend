from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_settings import CompanySettings
from app.schemas.company_settings import CompanySettingsUpsert


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
