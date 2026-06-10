from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment_record import PaymentRecord
from app.schemas.payment_record import PaymentRecordCreate
from app.services.invoice_service import InvoiceNotFoundError, quantize_money


class PaymentNotFoundError(ValueError):
    pass


def get_payments(db: Session, device_id: str) -> list[PaymentRecord]:
    statement = (
        select(PaymentRecord)
        .where(PaymentRecord.device_id == device_id)
        .order_by(
            PaymentRecord.payment_date.desc(),
            PaymentRecord.id.desc(),
        )
    )
    return list(db.scalars(statement).all())


def get_invoice_payments(
    db: Session,
    invoice_id: int,
    device_id: str,
) -> list[PaymentRecord]:
    invoice = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.device_id == device_id)
    )
    if invoice is None:
        raise InvoiceNotFoundError("Invoice not found")

    statement = (
        select(PaymentRecord)
        .where(
            PaymentRecord.invoice_id == invoice_id,
            PaymentRecord.device_id == device_id,
        )
        .order_by(PaymentRecord.payment_date.desc(), PaymentRecord.id.desc())
    )
    return list(db.scalars(statement).all())


def get_payment(
    db: Session,
    payment_id: int,
    device_id: str,
) -> PaymentRecord | None:
    statement = select(PaymentRecord).where(
        PaymentRecord.id == payment_id,
        PaymentRecord.device_id == device_id,
    )
    return db.scalar(statement)


def create_payment(
    db: Session,
    payload: PaymentRecordCreate,
    device_id: str,
    invoice_id: int | None = None,
) -> PaymentRecord:
    target_invoice_id = invoice_id if invoice_id is not None else payload.invoice_id
    invoice: Invoice | None = None

    if target_invoice_id is not None:
        invoice = db.scalar(
            select(Invoice).where(
                Invoice.id == target_invoice_id,
                Invoice.device_id == device_id,
            )
        )
        if invoice is None:
            raise InvoiceNotFoundError("Invoice not found")

    payment = PaymentRecord(
        device_id=device_id,
        invoice_id=invoice.id if invoice else None,
        amount=quantize_money(payload.amount),
        payment_date=payload.payment_date,
        payment_method=payload.payment_method,
        reference=payload.reference,
        notes=payload.notes,
    )
    db.add(payment)
    db.flush()

    if invoice is not None:
        paid_amount = db.scalar(
            select(
                func.coalesce(func.sum(PaymentRecord.amount), Decimal("0.00"))
            ).where(
                PaymentRecord.invoice_id == invoice.id,
                PaymentRecord.device_id == device_id,
            )
        )
        paid_amount = quantize_money(paid_amount or Decimal("0.00"))

        if paid_amount >= invoice.total:
            invoice.status = "paid"
        elif paid_amount > Decimal("0.00"):
            invoice.status = "partially_paid"

    db.commit()
    db.refresh(payment)
    return payment
