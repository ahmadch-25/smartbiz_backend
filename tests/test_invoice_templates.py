from collections.abc import Generator
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from weasyprint import HTML

import app.models  # noqa: F401
from app.constants.dummy_template_context import SAMPLE_PREVIEW_CONTEXT
from app.constants.invoice_templates import (
    INVOICE_TEMPLATE_DEFINITIONS,
    INVOICE_TEMPLATE_DIR,
    TEMPLATE_PREVIEW_DIR,
)
from app.db.base import Base
from app.db.database import get_db
from app.main import app as fastapi_app
from app.models.invoice_template import InvoiceTemplate
from app.routers.invoice_templates import (
    PREVIEW_ENVIRONMENT,
    preview_invoice_template,
)
from app.services.invoice_template_service import (
    get_active_invoice_templates,
    soft_delete_invoice_template,
)
from app.services.pdf_service import PdfService
from app.services.seed_invoice_templates import seed_invoice_templates


def make_invoice(item_count: int = 2):
    items = [
        SimpleNamespace(
            product_name=f"Service {index}",
            description=f"Description for service {index}",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            line_total=Decimal("100.00"),
        )
        for index in range(1, item_count + 1)
    ]
    subtotal = Decimal(item_count * 100)
    return SimpleNamespace(
        invoice_number="INV-TEST-1001",
        issue_date=date(2026, 8, 1),
        due_date=date(2026, 8, 15),
        status="partially_paid",
        notes="Thank you for your business.",
        client_name="Test Client",
        client_address="45 Client Avenue\nKarachi",
        client_email="client@example.com",
        client_phone="+92 300 0000000",
        subtotal=subtotal,
        tax=Decimal("10.00"),
        discount=Decimal("5.00"),
        total=subtotal + Decimal("5.00"),
        items=items,
        payments=[SimpleNamespace(amount=Decimal("25.00"))],
    )


def make_company_settings():
    return SimpleNamespace(
        company_name="SmartBiz Test Company",
        address="123 Business Street\nKarachi",
        email="billing@example.com",
        phone="+92 21 0000000",
        logo_url=None,
        website="example.com",
        tax_number="NTN-12345",
        registration_number=None,
        default_currency="PKR",
    )


def make_template_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_registered_template_assets_exist():
    for definition in INVOICE_TEMPLATE_DEFINITIONS:
        assert (INVOICE_TEMPLATE_DIR / definition.filename).is_file()
        assert (TEMPLATE_PREVIEW_DIR / definition.preview_filename).is_file()


def test_all_registered_templates_render_with_invoice_context():
    service = PdfService(INVOICE_TEMPLATE_DIR)
    invoice = make_invoice()
    settings = make_company_settings()

    for definition in INVOICE_TEMPLATE_DEFINITIONS:
        pdf_bytes = service.generate_invoice_pdf(
            invoice=invoice,
            template_key=definition.key,
            company_settings=settings,
        )
        assert pdf_bytes.startswith(b"%PDF"), definition.key


def test_invoice_context_uses_raw_money_currency_and_payment_balance():
    service = PdfService(INVOICE_TEMPLATE_DIR)
    context = service._build_invoice_context(
        make_invoice(),
        make_company_settings(),
    )

    assert context["invoice"]["currency"] == "PKR "
    assert context["invoice"]["issue_date"] == "August 1, 2026"
    assert context["company"]["address_lines"] == [
        "123 Business Street",
        "Karachi",
    ]
    assert context["items"][0]["description"] == "Service 1"
    assert context["items"][0]["unit_price"] == Decimal("100.00")
    assert context["items"][0]["amount"] == Decimal("100.00")
    assert context["totals"]["amount_paid"] == Decimal("25.00")
    assert context["totals"]["balance_due"] == Decimal("180.00")


def test_monogram_reference_layout_stays_on_one_page():
    sample_items = cast(list[dict[str, Any]], SAMPLE_PREVIEW_CONTEXT["items"])
    sample_invoice = cast(dict[str, Any], SAMPLE_PREVIEW_CONTEXT["invoice"])
    context = {
        **SAMPLE_PREVIEW_CONTEXT,
        "items": sample_items * 3,
        "invoice": {
            **sample_invoice,
            "terms": "Payment is due within 30 days of the issue date.",
            "payment_details": {
                "method_label": "Bank transfer",
                "lines": ["Account: 123456789", "Bank: Example Bank"],
            },
        },
    }
    template = PREVIEW_ENVIRONMENT.get_template("10_monogram_fine.html")
    html = template.render(**context)
    document = HTML(string=html, base_url=str(INVOICE_TEMPLATE_DIR)).render()

    assert len(document.pages) == 1


def test_html_preview_renders_jinja_context():
    response = preview_invoice_template("01_classic_ledger")
    html = response.body.decode()

    assert "INV-1001" in html
    assert "{{" not in html
    assert "{%" not in html


def test_template_catalog_sync_is_idempotent_and_filters_unknown_keys():
    with make_template_session() as db:
        assert seed_invoice_templates(db) == len(INVOICE_TEMPLATE_DEFINITIONS)
        assert seed_invoice_templates(db) == 0

        db.add(
            InvoiceTemplate(
                name="Unknown",
                key="unknown_template",
                preview_image="/static/template_previews/unknown.png",
            )
        )
        db.commit()

        rows = list(db.scalars(select(InvoiceTemplate)).all())
        active_templates = get_active_invoice_templates(db)

        assert len(rows) == len(INVOICE_TEMPLATE_DEFINITIONS) + 1
        assert [template.key for template in active_templates] == [
            definition.key for definition in INVOICE_TEMPLATE_DEFINITIONS
        ]

        assert soft_delete_invoice_template(db, active_templates[0].id) is True
        assert seed_invoice_templates(db) == 0
        assert active_templates[0].is_active is False


def test_template_list_api_shape_remains_backward_compatible():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        seed_invoice_templates(db)

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as db:
            yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(fastapi_app, raise_server_exceptions=False)
        response = client.get("/invoice-templates")
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] is True
        assert payload["message"] == "success"
        assert [row["key"] for row in payload["result"]] == [
            definition.key for definition in INVOICE_TEMPLATE_DEFINITIONS
        ]
        assert set(payload["result"][0]) == {
            "id",
            "name",
            "key",
            "description",
            "preview_image",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert payload["result"][0]["preview_image"].startswith(
            "http://testserver/static/template_previews/"
        )
    finally:
        fastapi_app.dependency_overrides.clear()
