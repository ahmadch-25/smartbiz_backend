from collections.abc import Generator
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.database import get_db
from app.main import app as fastapi_app
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.payment_record import PaymentRecord

DEVICE_A = "11111111-1111-1111-1111-111111111111"
DEVICE_B = "22222222-2222-2222-2222-222222222222"


def make_test_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    return TestClient(fastapi_app, raise_server_exceptions=False), testing_session


def clear_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


def seed_invoice(
    db: Session,
    device_id: str,
    invoice_number: str,
    status: str,
    total: Decimal,
    paid_amount: Decimal | None = None,
) -> Invoice:
    client = Client(device_id=device_id, name=f"Client {device_id[:4]}")
    invoice = Invoice(
        device_id=device_id,
        client=client,
        invoice_number=invoice_number,
        issue_date=date(2026, 6, 10),
        due_date=date(2026, 6, 24),
        status=status,
        client_name=client.name,
        subtotal=total,
        tax=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=total,
    )
    db.add(invoice)
    db.flush()

    if paid_amount is not None:
        db.add(
            PaymentRecord(
                device_id=device_id,
                invoice_id=invoice.id,
                amount=paid_amount,
                payment_date=date(2026, 6, 10),
                payment_method="cash",
            )
        )

    db.commit()
    db.refresh(invoice)
    return invoice


def test_dashboard_requires_device_id():
    client, _ = make_test_client()
    try:
        response = client.get("/dashboard")
        assert response.status_code == 400
        assert response.json()["message"] == "X-Device-Id header is required"
    finally:
        clear_overrides()


def test_dashboard_summary_is_scoped_by_device():
    client, session_factory = make_test_client()
    try:
        with session_factory() as db:
            seed_invoice(
                db,
                DEVICE_A,
                "INV-A-1",
                "partially_paid",
                Decimal("100.00"),
                Decimal("40.00"),
            )
            seed_invoice(
                db,
                DEVICE_A,
                "INV-A-2",
                "draft",
                Decimal("50.00"),
            )
            seed_invoice(
                db,
                DEVICE_B,
                "INV-B-1",
                "paid",
                Decimal("999.00"),
                Decimal("999.00"),
            )

        response = client.get("/dashboard", headers={"X-Device-Id": DEVICE_A})
        assert response.status_code == 200

        result = response.json()["result"]
        assert result["clients_count"] == 2
        assert result["invoices_count"] == 2
        assert result["draft_invoices_count"] == 1
        assert result["partially_paid_invoices_count"] == 1
        assert result["paid_invoices_count"] == 0
        assert result["total_sales"] == "150.00"
        assert result["total_paid"] == "40.00"
        assert result["total_due"] == "110.00"
        assert [invoice["invoice_number"] for invoice in result["recent_invoices"]] == [
            "INV-A-2",
            "INV-A-1",
        ]
        assert len(result["recent_payments"]) == 1
    finally:
        clear_overrides()
