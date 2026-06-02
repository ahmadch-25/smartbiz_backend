from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.api_response import ApiResponse


class InvoiceTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    key: str = Field(..., min_length=1, max_length=80)
    description: str | None = None
    preview_image: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class InvoiceTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    preview_image: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class InvoiceTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    key: str
    description: str | None
    preview_image: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


InvoiceTemplateResponse = ApiResponse[InvoiceTemplateOut]
InvoiceTemplateListResponse = ApiResponse[list[InvoiceTemplateOut]]
