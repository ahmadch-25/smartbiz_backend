from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.api_response import ApiResponse
from app.schemas.invoice import InvoiceOut


class AiInvoiceDraftRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ExtractedInvoiceItem(BaseModel):
    product_name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    quantity: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    unit: str | None = Field(default=None, max_length=40)


class OllamaInvoiceItemExtraction(BaseModel):
    product_name: str = Field(
        description="Product or service name. Use an empty string if missing."
    )
    description: str = Field(
        description="Optional item description. Use an empty string if missing."
    )
    quantity: float = Field(
        description="Quantity sold. Use 0 when missing or uncertain."
    )
    unit_price: float = Field(
        description="Unit price only. Use 0 when missing or uncertain."
    )
    unit: str = Field(
        description="Unit such as each, kg, hour. Use an empty string if missing."
    )


class OllamaInvoiceExtraction(BaseModel):
    client_name: str = Field(
        description="Client name only when clearly provided. Use an empty string if missing."
    )
    client_id: int = Field(
        description="Existing client id if explicitly provided. Use 0 otherwise."
    )
    currency: str = Field(description="Three-letter currency code such as USD or PKR.")
    items: list[OllamaInvoiceItemExtraction] = Field(
        description="Extracted invoice line items."
    )
    missing_fields: list[str] = Field(
        description="Missing or uncertain fields, for example client or items[0].unit_price."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Extraction confidence from 0 to 1.",
    )


class ExtractedInvoiceData(BaseModel):
    client_name: str | None = Field(default=None, max_length=150)
    client_id: int | None = None
    currency: str = Field(default="USD", max_length=3)
    items: list[ExtractedInvoiceItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class InvoiceDraftConfirmationOption(BaseModel):
    field: str
    message: str
    options: list[str] = Field(default_factory=list)


class AiInvoiceDraftResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    needs_confirmation: bool
    missing_fields: list[str]
    confirmation_options: list[InvoiceDraftConfirmationOption] = Field(
        default_factory=list
    )
    extracted: ExtractedInvoiceData
    invoice: InvoiceOut | None = None


AiInvoiceDraftResponse = ApiResponse[AiInvoiceDraftResult]
