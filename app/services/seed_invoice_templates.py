from sqlalchemy.orm import Session

from app.schemas.invoice_template import InvoiceTemplateCreate
from app.services.invoice_template_service import (
    DuplicateTemplateKeyError,
    create_invoice_template,
)


DEFAULT_INVOICE_TEMPLATES = [
    InvoiceTemplateCreate(
        name="Modern",
        key="modern_1",
        description="Clean blue business invoice with clear totals and payment details.",
        preview_image="/invoice-templates/preview/modern_1",
    ),
    InvoiceTemplateCreate(
        name="Classic",
        key="classic_1",
        description="Traditional serif invoice with formal spacing and borders.",
        preview_image="/invoice-templates/preview/classic_1",
    ),
    InvoiceTemplateCreate(
        name="Minimal",
        key="minimal_1",
        description="Plain, spacious invoice layout for simple professional documents.",
        preview_image="/invoice-templates/preview/minimal_1",
    ),
    InvoiceTemplateCreate(
        name="Corporate",
        key="corporate_1",
        description="Structured corporate invoice with a strong header and summary blocks.",
        preview_image="/invoice-templates/preview/corporate_1",
    ),
    InvoiceTemplateCreate(
        name="Retail",
        key="retail_1",
        description="Friendly retail-style invoice with highlighted totals.",
        preview_image="/invoice-templates/preview/retail_1",
    ),
]


def seed_invoice_templates(db: Session) -> int:
    created_count = 0
    for template in DEFAULT_INVOICE_TEMPLATES:
        try:
            create_invoice_template(db, template)
        except DuplicateTemplateKeyError:
            continue
        created_count += 1
    return created_count
