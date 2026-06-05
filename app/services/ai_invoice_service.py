from datetime import date, timedelta
from decimal import Decimal
import logging
import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.schemas.ai_invoice import (
    AiInvoiceDraftResult,
    ExtractedInvoiceData,
    ExtractedInvoiceItem,
    InvoiceDraftConfirmationOption,
    OllamaInvoiceExtraction,
)
from app.schemas.invoice import InvoiceOut
from app.services.invoice_service import generate_invoice_number, quantize_money

logger = logging.getLogger(__name__)


class AiInvoiceExtractionError(ValueError):
    pass


class AiInvoiceDraftError(ValueError):
    pass


EXTRACTION_PROMPT = """Extract invoice draft data from the user's text.

Rules:
- Return only structured data matching the provided schema.
- Do not calculate line totals, subtotal, tax, discount, or total.
- Extract client_name only when the user clearly names who the invoice is for.
- If no client is mentioned, use empty client_name, client_id 0, and add "client" to missing_fields.
- Extract each sold product as an item with product_name, quantity, unit_price, and unit when present.
- Support Roman Urdu / Hinglish phrasing. Examples:
  "30 shower set aik ki qemat 5000pkr" means quantity 30, product_name "shower set", unit_price 5000, unit "each".
  "20 commod aik ki qemat 10000pkr" means quantity 20, product_name "commod", unit_price 10000, unit "each".
  "toseef ko bechy hain" means client_name "toseef".
- Do not include quantity words/numbers in product_name.
- Use empty strings for missing text fields.
- Use 0 for missing or uncertain numeric fields.
- Use USD as the default currency when the user uses "$".
- If product name, quantity, or unit price is missing or uncertain, add the exact field path to missing_fields.
- Set confidence from 0 to 1 based on extraction certainty.
"""

LEADING_QUANTITY_PATTERN = re.compile(
    r"^\s*(?P<quantity>\d+(?:\.\d+)?)\s+(?P<name>.+)$"
)
CLIENT_KO_PATTERN = re.compile(
    r"\b(?P<client>[a-zA-Z][a-zA-Z0-9_-]{1,80})\s+ko\s+"
    r"(?:bech|bechy|bechi|sell|sells|sale|di|diya|dye)\b",
    re.IGNORECASE,
)


def normalize_ollama_extraction(
    extraction: OllamaInvoiceExtraction,
) -> ExtractedInvoiceData:
    return ExtractedInvoiceData(
        client_name=extraction.client_name.strip() or None,
        client_id=extraction.client_id or None,
        currency=(extraction.currency.strip().upper() or "USD")[:3],
        items=[
            ExtractedInvoiceItem(
                product_name=item.product_name.strip() or None,
                description=item.description.strip() or None,
                quantity=Decimal(str(item.quantity)) if item.quantity > 0 else None,
                unit_price=Decimal(str(item.unit_price))
                if item.unit_price > 0
                else None,
                unit=item.unit.strip() or None,
            )
            for item in extraction.items
        ],
        missing_fields=extraction.missing_fields,
        confidence=extraction.confidence,
    )


def apply_text_fallbacks(
    text: str,
    extracted: ExtractedInvoiceData,
) -> ExtractedInvoiceData:
    if not extracted.client_name:
        client_match = CLIENT_KO_PATTERN.search(text)
        if client_match:
            extracted.client_name = client_match.group("client").strip()
            extracted.missing_fields = [
                field for field in extracted.missing_fields if field != "client"
            ]

    for item in extracted.items:
        if not item.product_name:
            continue

        quantity_match = LEADING_QUANTITY_PATTERN.match(item.product_name)
        if not quantity_match:
            continue

        parsed_quantity = Decimal(quantity_match.group("quantity"))
        parsed_name = quantity_match.group("name").strip()

        if item.quantity is None or item.quantity == Decimal("1"):
            item.quantity = parsed_quantity
        item.product_name = parsed_name

    return extracted


def get_structured_invoice_extractor() -> Any:
    provider = settings.AI_PROVIDER

    if provider == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise AiInvoiceExtractionError(
                "ANTHROPIC_API_KEY is required when AI_PROVIDER=claude"
            )

        llm = ChatAnthropic(
            model_name=settings.CLAUDE_MODEL_NAME,
            api_key=SecretStr(settings.ANTHROPIC_API_KEY),
            temperature=0,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        return llm.with_structured_output(OllamaInvoiceExtraction)

    if provider == "ollama":
        llm = ChatOllama(
            model=settings.OLLAMA_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
        )
        return llm.with_structured_output(OllamaInvoiceExtraction)

    raise AiInvoiceExtractionError(
        f"Unsupported AI_PROVIDER '{settings.AI_PROVIDER}'. Use 'claude' or 'ollama'."
    )


def extract_invoice_data(text: str) -> ExtractedInvoiceData:
    if not text.strip():
        raise AiInvoiceExtractionError("Invoice text is required")

    structured_llm = get_structured_invoice_extractor()

    try:
        result = structured_llm.invoke(
            [
                ("system", EXTRACTION_PROMPT),
                ("human", text),
            ]
        )
    except Exception as exc:
        logger.exception("AI invoice extraction failed")
        raise AiInvoiceExtractionError("Could not extract invoice data") from exc

    try:
        extraction = OllamaInvoiceExtraction.model_validate(result)
        extracted = normalize_ollama_extraction(extraction)
        return apply_text_fallbacks(text, extracted)
    except ValidationError as exc:
        logger.exception("AI invoice extraction returned invalid output")
        raise AiInvoiceExtractionError("Invalid AI extraction output") from exc


def get_extraction_issues(
    extracted: ExtractedInvoiceData,
) -> tuple[list[str], list[InvoiceDraftConfirmationOption]]:
    missing_fields = list(dict.fromkeys(extracted.missing_fields))
    confirmation_options: list[InvoiceDraftConfirmationOption] = []

    if (
        not extracted.client_name
        and extracted.client_id is None
        and "client" not in missing_fields
    ):
        missing_fields.append("client")

    if not extracted.items:
        if "items" not in missing_fields:
            missing_fields.append("items")
        confirmation_options.append(
            InvoiceDraftConfirmationOption(
                field="items",
                message="No invoice items were found in the text.",
            )
        )
        return missing_fields, confirmation_options

    for index, item in enumerate(extracted.items):
        prefix = f"items[{index}]"
        item_missing = []
        if not item.product_name:
            item_missing.append(f"{prefix}.product_name")
        if item.quantity is None:
            item_missing.append(f"{prefix}.quantity")
        if item.unit_price is None:
            item_missing.append(f"{prefix}.unit_price")

        for field in item_missing:
            if field not in missing_fields:
                missing_fields.append(field)

        if item_missing:
            confirmation_options.append(
                InvoiceDraftConfirmationOption(
                    field=prefix,
                    message="This item is missing required product information.",
                    options=[],
                )
            )

    if extracted.confidence < 0.65:
        confirmation_options.append(
            InvoiceDraftConfirmationOption(
                field="extraction",
                message="The AI extraction confidence is low. Please confirm the draft.",
                options=[],
            )
        )

    return missing_fields, confirmation_options


def has_blocking_item_issues(missing_fields: list[str]) -> bool:
    return any(
        field == "items" or field.startswith("items[") for field in missing_fields
    )


def create_draft_invoice_from_extraction(
    db: Session,
    extracted: ExtractedInvoiceData,
) -> Invoice:
    if not extracted.items:
        raise AiInvoiceDraftError("At least one invoice item is required")

    client: Client | None = None
    if extracted.client_id is not None:
        client = db.get(Client, extracted.client_id)
        if client is None:
            raise AiInvoiceDraftError(
                "Extracted client_id does not match an existing client"
            )
    elif extracted.client_name:
        client = Client(name=extracted.client_name)
        db.add(client)
        db.flush()

    invoice_items: list[InvoiceItem] = []
    subtotal = Decimal("0.00")

    for item in extracted.items:
        if not item.product_name or item.quantity is None or item.unit_price is None:
            raise AiInvoiceDraftError("Invoice item is missing required fields")

        quantity = item.quantity
        unit_price = quantize_money(item.unit_price)
        line_total = quantize_money(quantity * unit_price)
        subtotal += line_total

        invoice_items.append(
            InvoiceItem(
                product_name=item.product_name,
                description=item.description,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    today = date.today()
    subtotal = quantize_money(subtotal)
    invoice = Invoice(
        client_id=client.id if client else None,
        invoice_number=generate_invoice_number(db),
        issue_date=today,
        due_date=today + timedelta(days=14),
        status="draft",
        notes=None,
        template_key=None,
        client_name=client.name if client else None,
        client_email=client.email if client else None,
        client_phone=client.phone if client else None,
        client_address=client.address if client else None,
        subtotal=subtotal,
        tax=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=subtotal,
        items=invoice_items,
    )

    db.add(invoice)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = str(exc.orig).lower()
        if "client_id" in message and ("not-null" in message or "not null" in message):
            raise AiInvoiceDraftError(
                "Database migration required: run `uv run alembic upgrade head` "
                "so draft invoices can be saved without a client."
            ) from exc
        raise AiInvoiceDraftError("Could not create draft invoice") from exc
    db.refresh(invoice)
    return invoice


def build_ai_invoice_draft(
    db: Session,
    text: str,
) -> AiInvoiceDraftResult:
    extracted = extract_invoice_data(text)
    missing_fields, confirmation_options = get_extraction_issues(extracted)
    needs_confirmation = bool(missing_fields or confirmation_options)

    if has_blocking_item_issues(missing_fields):
        return AiInvoiceDraftResult(
            needs_confirmation=True,
            missing_fields=missing_fields,
            confirmation_options=confirmation_options,
            extracted=extracted,
            invoice=None,
        )

    invoice = create_draft_invoice_from_extraction(db, extracted)

    return AiInvoiceDraftResult(
        needs_confirmation=needs_confirmation,
        missing_fields=missing_fields,
        confirmation_options=confirmation_options,
        extracted=extracted,
        invoice=InvoiceOut.model_validate(invoice),
    )
