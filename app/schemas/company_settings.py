from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.api_response import ApiResponse


class CompanySettingsUpsert(BaseModel):
    company_name: str | None = Field(default=None, max_length=150)
    logo_url: str | None = Field(default=None, max_length=500)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    tax_number: str | None = Field(default=None, max_length=100)
    registration_number: str | None = Field(default=None, max_length=100)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)


class CompanySettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str | None
    logo_url: str | None
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    tax_number: str | None
    registration_number: str | None
    default_currency: str | None
    created_at: datetime
    updated_at: datetime


CompanySettingsResponse = ApiResponse[CompanySettingsOut]
