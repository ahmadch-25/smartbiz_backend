from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.api_response import ApiResponse


class PaymentRecordCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    payment_date: date
    payment_method: str | None = Field(default=None, max_length=80)
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class PaymentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    amount: Decimal
    payment_date: date
    payment_method: str | None
    reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


PaymentRecordResponse = ApiResponse[PaymentRecordOut]
PaymentRecordListResponse = ApiResponse[list[PaymentRecordOut]]
