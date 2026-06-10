from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.invoice import Invoice
from app.models.payment_record import PaymentRecord
from app.schemas.dashboard import DashboardSummaryOut
from app.schemas.invoice import InvoiceOut
from app.schemas.payment_record import PaymentRecordOut
from app.services.invoice_service import quantize_money


def count_invoices_by_status(db: Session, device_id: str, status: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.device_id == device_id, Invoice.status == status)
        )
        or 0
    )


def get_dashboard_summary(db: Session, device_id: str) -> DashboardSummaryOut:
    clients_count = int(
        db.scalar(
            select(func.count())
            .select_from(Client)
            .where(Client.device_id == device_id)
        )
        or 0
    )
    invoices_count = int(
        db.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.device_id == device_id)
        )
        or 0
    )
    total_sales = db.scalar(
        select(func.coalesce(func.sum(Invoice.total), Decimal("0.00"))).where(
            Invoice.device_id == device_id
        )
    )
    total_paid = db.scalar(
        select(func.coalesce(func.sum(PaymentRecord.amount), Decimal("0.00"))).where(
            PaymentRecord.device_id == device_id,
            PaymentRecord.invoice_id.is_not(None),
        )
    )

    total_sales = quantize_money(total_sales or Decimal("0.00"))
    total_paid = quantize_money(total_paid or Decimal("0.00"))
    total_due = max(total_sales - total_paid, Decimal("0.00"))

    recent_invoices = list(
        db.scalars(
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments))
            .where(Invoice.device_id == device_id)
            .order_by(Invoice.created_at.desc(), Invoice.id.desc())
            .limit(5)
        ).all()
    )
    recent_payments = list(
        db.scalars(
            select(PaymentRecord)
            .where(PaymentRecord.device_id == device_id)
            .order_by(PaymentRecord.payment_date.desc(), PaymentRecord.id.desc())
            .limit(5)
        ).all()
    )

    return DashboardSummaryOut(
        clients_count=clients_count,
        invoices_count=invoices_count,
        draft_invoices_count=count_invoices_by_status(db, device_id, "draft"),
        sent_invoices_count=count_invoices_by_status(db, device_id, "sent"),
        partially_paid_invoices_count=count_invoices_by_status(
            db, device_id, "partially_paid"
        ),
        paid_invoices_count=count_invoices_by_status(db, device_id, "paid"),
        overdue_invoices_count=count_invoices_by_status(db, device_id, "overdue"),
        total_sales=total_sales,
        total_paid=total_paid,
        total_due=quantize_money(total_due),
        recent_invoices=[
            InvoiceOut.model_validate(invoice) for invoice in recent_invoices
        ],
        recent_payments=[
            PaymentRecordOut.model_validate(payment) for payment in recent_payments
        ],
    )
