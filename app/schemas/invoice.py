from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.api_response import ApiResponse
from app.schemas.payment_record import PaymentRecordOut

InvoiceStatus = Literal["draft", "sent", "partially_paid", "paid", "overdue"]


class InvoiceItemCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)


class InvoiceCreate(BaseModel):
    client_id: int
    issue_date: date
    due_date: date
    notes: str | None = None
    template_key: str | None = Field(default=None, max_length=80)
    tax: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    discount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    items: list[InvoiceItemCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.due_date < self.issue_date:
            raise ValueError("due_date cannot be before issue_date")
        return self


class InvoiceUpdate(BaseModel):
    due_date: date | None = None
    notes: str | None = None
    template_key: str | None = Field(default=None, max_length=80)
    status: InvoiceStatus | None = None


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    product_name: str
    description: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime
    updated_at: datetime


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    invoice_number: str
    issue_date: date
    due_date: date
    status: str
    notes: str | None
    template_key: str | None
    client_name: str
    client_email: str | None
    client_phone: str | None
    client_address: str | None
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemOut] = Field(default_factory=list)
    payments: list[PaymentRecordOut] = Field(default_factory=list)


InvoiceResponse = ApiResponse[InvoiceOut]
InvoiceListResponse = ApiResponse[list[InvoiceOut]]
