from decimal import Decimal

import pytest
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.schemas.ai_invoice import (
    ExtractedInvoiceData,
    ExtractedInvoiceItem,
    OllamaInvoiceExtraction,
    OllamaInvoiceItemExtraction,
)
from app.services import ai_invoice_service


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    return testing_session()


def test_ai_invoice_draft_creates_client_and_invoice(monkeypatch):
    db = make_session()

    extracted = ExtractedInvoiceData(
        client_name="toseef",
        currency="USD",
        confidence=0.94,
        items=[
            ExtractedInvoiceItem(
                product_name="soap",
                quantity=Decimal("30"),
                unit_price=Decimal("5"),
                unit="each",
            ),
            ExtractedInvoiceItem(
                product_name="toys",
                quantity=Decimal("20"),
                unit_price=Decimal("10"),
                unit="each",
            ),
        ],
    )
    monkeypatch.setattr(
        ai_invoice_service, "extract_invoice_data", lambda text: extracted
    )

    result = ai_invoice_service.build_ai_invoice_draft(
        db,
        "sell 30 soap $5 each and 20 toys $10 each to toseef",
    )

    assert result.invoice is not None
    assert result.invoice.status == "draft"
    assert result.invoice.client_name == "toseef"
    assert result.invoice.client_id is not None
    assert result.invoice.subtotal == Decimal("350.00")
    assert result.invoice.total == Decimal("350.00")
    assert len(result.invoice.items) == 2
    assert result.needs_confirmation is False


def test_ai_invoice_draft_allows_missing_client(monkeypatch):
    db = make_session()

    extracted = ExtractedInvoiceData(
        currency="USD",
        confidence=0.9,
        items=[
            ExtractedInvoiceItem(
                product_name="soap",
                quantity=Decimal("30"),
                unit_price=Decimal("5"),
                unit="each",
            )
        ],
    )
    monkeypatch.setattr(
        ai_invoice_service, "extract_invoice_data", lambda text: extracted
    )

    result = ai_invoice_service.build_ai_invoice_draft(
        db,
        "sell 30 soap $5 each",
    )

    assert result.invoice is not None
    assert result.invoice.client_id is None
    assert result.invoice.client_name is None
    assert result.invoice.total == Decimal("150.00")
    assert result.needs_confirmation is True
    assert "client" in result.missing_fields


def test_ai_invoice_draft_missing_product_needs_confirmation(monkeypatch):
    db = make_session()

    extracted = ExtractedInvoiceData(
        client_name="toseef",
        currency="USD",
        confidence=0.5,
        items=[
            ExtractedInvoiceItem(
                product_name=None,
                quantity=Decimal("30"),
                unit_price=Decimal("5"),
                unit="each",
            )
        ],
    )
    monkeypatch.setattr(
        ai_invoice_service, "extract_invoice_data", lambda text: extracted
    )

    result = ai_invoice_service.build_ai_invoice_draft(
        db,
        "sell 30 something $5 each to toseef",
    )

    assert result.invoice is None
    assert result.needs_confirmation is True
    assert "items[0].product_name" in result.missing_fields
    assert result.confirmation_options


def test_roman_urdu_fallback_extracts_client_and_quantity_from_name():
    extraction = OllamaInvoiceExtraction(
        client_name="",
        client_id=0,
        currency="PKR",
        confidence=0.9,
        missing_fields=["client"],
        items=[
            OllamaInvoiceItemExtraction(
                product_name="30 shower set",
                description="",
                quantity=1,
                unit_price=5000,
                unit="each",
            ),
            OllamaInvoiceItemExtraction(
                product_name="20 commod",
                description="",
                quantity=1,
                unit_price=10000,
                unit="each",
            ),
        ],
    )

    extracted = ai_invoice_service.normalize_ollama_extraction(extraction)
    extracted = ai_invoice_service.apply_text_fallbacks(
        "aj me ne 30 shower set aik ki qemat 5000pkr the or 20 commod aik ki "
        "qemat 10000pkr the toseef ko bechy hain",
        extracted,
    )

    assert extracted.client_name == "toseef"
    assert "client" not in extracted.missing_fields
    assert extracted.items[0].product_name == "shower set"
    assert extracted.items[0].quantity == Decimal("30")
    assert extracted.items[1].product_name == "commod"
    assert extracted.items[1].quantity == Decimal("20")


def test_old_database_not_null_client_id_returns_clear_error(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    Table(
        "clients",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(150), nullable=False),
        Column("email", String(255), nullable=True),
        Column("phone", String(50), nullable=True),
        Column("address", String(500), nullable=True),
        Column("created_at", DateTime, nullable=True),
        Column("updated_at", DateTime, nullable=True),
    )
    Table(
        "invoices",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("client_id", Integer, ForeignKey("clients.id"), nullable=False),
        Column("invoice_number", String(40), nullable=False, unique=True),
        Column("issue_date", Date, nullable=False),
        Column("due_date", Date, nullable=False),
        Column("status", String(30), nullable=False),
        Column("notes", Text, nullable=True),
        Column("template_key", String(80), nullable=True),
        Column("client_name", String(150), nullable=True),
        Column("client_email", String(255), nullable=True),
        Column("client_phone", String(50), nullable=True),
        Column("client_address", String(500), nullable=True),
        Column("subtotal", Numeric(12, 2), nullable=False),
        Column("tax", Numeric(12, 2), nullable=False),
        Column("discount", Numeric(12, 2), nullable=False),
        Column("total", Numeric(12, 2), nullable=False),
        Column("created_at", DateTime, nullable=True),
        Column("updated_at", DateTime, nullable=True),
    )
    Table(
        "invoice_items",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("invoice_id", Integer, ForeignKey("invoices.id"), nullable=False),
        Column("product_name", String(200), nullable=False),
        Column("description", Text, nullable=True),
        Column("quantity", Numeric(12, 2), nullable=False),
        Column("unit_price", Numeric(12, 2), nullable=False),
        Column("line_total", Numeric(12, 2), nullable=False),
        Column("created_at", DateTime, nullable=True),
        Column("updated_at", DateTime, nullable=True),
    )
    Table(
        "payment_records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("invoice_id", Integer, ForeignKey("invoices.id"), nullable=False),
        Column("amount", Numeric(12, 2), nullable=False),
        Column("payment_date", Date, nullable=False),
        Column("payment_method", String(80), nullable=True),
        Column("reference", String(120), nullable=True),
        Column("notes", Text, nullable=True),
        Column("created_at", DateTime, nullable=True),
        Column("updated_at", DateTime, nullable=True),
    )
    metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    extracted = ExtractedInvoiceData(
        currency="PKR",
        confidence=0.9,
        items=[
            ExtractedInvoiceItem(
                product_name="shower set",
                quantity=Decimal("30"),
                unit_price=Decimal("5000"),
                unit="each",
            )
        ],
    )

    monkeypatch.setattr(
        ai_invoice_service, "extract_invoice_data", lambda text: extracted
    )

    with pytest.raises(ai_invoice_service.AiInvoiceDraftError) as exc:
        ai_invoice_service.build_ai_invoice_draft(db, "sell 30 shower set")

    assert "alembic upgrade head" in str(exc.value)


def test_claude_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(ai_invoice_service.settings, "AI_PROVIDER", "claude")
    monkeypatch.setattr(ai_invoice_service.settings, "ANTHROPIC_API_KEY", None)

    with pytest.raises(ai_invoice_service.AiInvoiceExtractionError) as exc:
        ai_invoice_service.get_structured_invoice_extractor()

    assert "ANTHROPIC_API_KEY" in str(exc.value)


def test_claude_provider_builds_structured_extractor(monkeypatch):
    class FakeClaude:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def with_structured_output(self, schema):
            return {"schema": schema, "kwargs": self.kwargs}

    monkeypatch.setattr(ai_invoice_service.settings, "AI_PROVIDER", "claude")
    monkeypatch.setattr(ai_invoice_service.settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(ai_invoice_service.settings, "CLAUDE_MODEL_NAME", "claude-test")
    monkeypatch.setattr(ai_invoice_service, "ChatAnthropic", FakeClaude)

    extractor = ai_invoice_service.get_structured_invoice_extractor()

    assert extractor["schema"] is OllamaInvoiceExtraction
    assert extractor["kwargs"]["model_name"] == "claude-test"
