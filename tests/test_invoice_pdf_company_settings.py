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
from app.dependencies import get_pdf_service
from app.main import app as fastapi_app
from app.models.company_settings import CompanySettings
from app.models.invoice import Invoice
from app.services.pdf_service import PdfService

DEVICE_ID = "11111111-1111-1111-1111-111111111111"


class FakePdfService:
    def __init__(self):
        self.company_settings = None

    def generate_invoice_pdf(self, invoice, template_key: str, company_settings=None):
        self.company_settings = company_settings
        return b"%PDF-1.4 fake"


def make_test_client() -> tuple[TestClient, sessionmaker[Session], FakePdfService]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    fake_pdf_service = FakePdfService()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    def override_pdf_service():
        return fake_pdf_service

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_pdf_service] = override_pdf_service
    return (
        TestClient(fastapi_app, raise_server_exceptions=False),
        testing_session,
        fake_pdf_service,
    )


def clear_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


def seed_invoice(db: Session) -> Invoice:
    invoice = Invoice(
        device_id=DEVICE_ID,
        invoice_number="INV-PDF-1",
        issue_date=date(2026, 6, 12),
        due_date=date(2026, 6, 26),
        status="draft",
        client_name="Client Name",
        subtotal=Decimal("100.00"),
        tax=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("100.00"),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def test_pdf_context_uses_company_settings():
    pdf_service = PdfService(templates_dir="app/templates/invoices")
    invoice = Invoice(
        device_id=DEVICE_ID,
        invoice_number="INV-CONTEXT-1",
        issue_date=date(2026, 6, 12),
        due_date=date(2026, 6, 26),
        status="draft",
        client_name="Client Name",
        subtotal=Decimal("100.00"),
        tax=Decimal("0.00"),
        discount=Decimal("0.00"),
        total=Decimal("100.00"),
    )
    settings = CompanySettings(
        device_id=DEVICE_ID,
        company_name="My Company",
        logo_url="https://example.com/logo.png",
        address="Company Address",
        email="hello@example.com",
        phone="+920000000",
    )

    context = pdf_service._build_invoice_context(invoice, settings)

    assert context["company"]["name"] == "My Company"
    assert context["company"]["logo_url"] == "https://example.com/logo.png"
    assert context["company"]["address"] == "Company Address"
    assert context["company"]["email"] == "hello@example.com"
    assert context["company"]["phone"] == "+920000000"


def test_preview_pdf_passes_saved_company_settings_to_pdf_service():
    client, session_factory, fake_pdf_service = make_test_client()
    try:
        with session_factory() as db:
            invoice = seed_invoice(db)
            invoice_id = invoice.id
            db.add(
                CompanySettings(
                    device_id=DEVICE_ID,
                    company_name="Saved Company",
                    logo_url="https://example.com/logo.png",
                    address="Saved Address",
                )
            )
            db.commit()

        response = client.get(
            f"/invoices/{invoice_id}/preview-pdf?template_key=modern_1",
            headers={"X-Device-Id": DEVICE_ID},
        )

        assert response.status_code == 200
        assert fake_pdf_service.company_settings is not None
        assert fake_pdf_service.company_settings.company_name == "Saved Company"
        assert fake_pdf_service.company_settings.logo_url == "https://example.com/logo.png"
    finally:
        clear_overrides()
