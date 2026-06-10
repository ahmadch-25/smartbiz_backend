from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.client import Client
from app.models.invoice import Invoice
from app.schemas.payment_record import PaymentRecordCreate
from app.services import payment_service

DEVICE_ID = "11111111-1111-1111-1111-111111111111"


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    return testing_session()


def create_invoice(db: Session, total: Decimal = Decimal("100.00")) -> Invoice:
    client = Client(name="Toseef", device_id=DEVICE_ID)
    invoice = Invoice(
        device_id=DEVICE_ID,
        client=client,
        invoice_number="INV-TEST-1",
        issue_date=date(2026, 6, 5),
        due_date=date(2026, 6, 19),
        status="draft",
        client_name="Toseef",
        subtotal=total,
        tax=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=total,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def test_invoice_payment_updates_status_to_partially_paid_then_paid():
    db = make_session()
    invoice = create_invoice(db)

    first_payment = payment_service.create_payment(
        db,
        PaymentRecordCreate(
            invoice_id=invoice.id,
            amount=Decimal("40.00"),
            payment_date=date(2026, 6, 5),
            payment_method="cash",
        ),
        DEVICE_ID,
    )
    db.refresh(invoice)

    assert first_payment.invoice_id == invoice.id
    assert invoice.status == "partially_paid"

    second_payment = payment_service.create_payment(
        db,
        PaymentRecordCreate(
            invoice_id=invoice.id,
            amount=Decimal("60.00"),
            payment_date=date(2026, 6, 6),
            payment_method="cash",
        ),
        DEVICE_ID,
    )
    db.refresh(invoice)

    assert second_payment.invoice_id == invoice.id
    assert invoice.status == "paid"


def test_standalone_payment_record_does_not_require_invoice():
    db = make_session()

    payment = payment_service.create_payment(
        db,
        PaymentRecordCreate(
            amount=Decimal("250.00"),
            payment_date=date(2026, 6, 5),
            payment_method="cash",
            notes="Personal payment record",
        ),
        DEVICE_ID,
    )

    assert payment.id is not None
    assert payment.invoice_id is None
    assert payment.amount == Decimal("250.00")
