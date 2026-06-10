from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

MONEY_QUANT = Decimal("0.01")


class ClientNotFoundError(ValueError):
    pass


class InvoiceNotFoundError(ValueError):
    pass


class InvalidInvoiceError(ValueError):
    pass


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def generate_invoice_number(db: Session) -> str:
    today = datetime.now(UTC).strftime("%Y%m%d")
    for _ in range(10):
        candidate = f"INV-{today}-{token_hex(3).upper()}"
        exists = db.scalar(
            select(Invoice.id).where(Invoice.invoice_number == candidate)
        )
        if exists is None:
            return candidate
    raise InvalidInvoiceError("Could not generate a unique invoice number")


def get_invoice_with_details(
    db: Session,
    invoice_id: int,
    device_id: str,
) -> Invoice | None:
    statement = (
        select(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.payments))
        .where(Invoice.id == invoice_id, Invoice.device_id == device_id)
    )
    return db.scalar(statement)


def get_invoices(db: Session, device_id: str) -> list[Invoice]:
    statement = (
        select(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.payments))
        .where(Invoice.device_id == device_id)
        .order_by(Invoice.id.desc())
    )
    return list(db.scalars(statement).all())


def create_invoice(db: Session, payload: InvoiceCreate, device_id: str) -> Invoice:
    client: Client | None = None
    if payload.client_id is not None:
        client = db.scalar(
            select(Client).where(
                Client.id == payload.client_id,
                Client.device_id == device_id,
            )
        )
        if client is None:
            raise ClientNotFoundError("Client not found")

    invoice_items: list[InvoiceItem] = []
    subtotal = Decimal("0.00")

    for item_payload in payload.items:
        line_total = quantize_money(item_payload.quantity * item_payload.unit_price)
        subtotal += line_total
        invoice_items.append(
            InvoiceItem(
                device_id=device_id,
                product_name=item_payload.product_name,
                description=item_payload.description,
                quantity=item_payload.quantity,
                unit_price=quantize_money(item_payload.unit_price),
                line_total=line_total,
            )
        )

    subtotal = quantize_money(subtotal)
    tax = quantize_money(payload.tax)
    discount = quantize_money(payload.discount)
    total = quantize_money(subtotal + tax - discount)

    if total < Decimal("0.00"):
        raise InvalidInvoiceError("Discount cannot exceed subtotal plus tax")

    invoice = Invoice(
        device_id=device_id,
        client_id=client.id if client else None,
        invoice_number=generate_invoice_number(db),
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        status="draft",
        notes=payload.notes,
        template_key=payload.template_key,
        client_name=client.name if client else None,
        client_email=client.email if client else None,
        client_phone=client.phone if client else None,
        client_address=client.address if client else None,
        subtotal=subtotal,
        tax=tax,
        discount=discount,
        total=total,
        items=invoice_items,
    )

    db.add(invoice)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise InvalidInvoiceError("Invoice number already exists") from exc
    return get_invoice_with_details(db, invoice.id, device_id) or invoice


def update_invoice(
    db: Session,
    invoice_id: int,
    payload: InvoiceUpdate,
    device_id: str,
) -> Invoice | None:
    invoice = get_invoice_with_details(db, invoice_id, device_id)
    if invoice is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    if "due_date" in update_data and update_data["due_date"] < invoice.issue_date:
        raise InvalidInvoiceError("due_date cannot be before issue_date")

    for field, value in update_data.items():
        setattr(invoice, field, value)

    db.commit()
    return get_invoice_with_details(db, invoice.id, device_id) or invoice


def delete_invoice(db: Session, invoice_id: int, device_id: str) -> bool:
    invoice = get_invoice_with_details(db, invoice_id, device_id)
    if invoice is None:
        return False

    db.delete(invoice)
    db.commit()
    return True
