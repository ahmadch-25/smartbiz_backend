from sqlalchemy.orm import Session

from app.constants.invoice_templates import INVOICE_TEMPLATE_DEFINITIONS
from app.schemas.invoice_template import InvoiceTemplateCreate
from app.services.invoice_template_service import (
    DuplicateTemplateKeyError,
    create_invoice_template,
    get_invoice_template_by_key,
)


DEFAULT_INVOICE_TEMPLATES = [
    InvoiceTemplateCreate(
        name=definition.name,
        key=definition.key,
        description=definition.description,
        preview_image=definition.preview_url,
    )
    for definition in INVOICE_TEMPLATE_DEFINITIONS
]


def seed_invoice_templates(db: Session) -> int:
    created_count = 0
    for template in DEFAULT_INVOICE_TEMPLATES:
        existing = get_invoice_template_by_key(db, template.key)
        if existing is not None:
            existing.name = template.name
            existing.description = template.description
            existing.preview_image = template.preview_image
            continue

        try:
            create_invoice_template(db, template)
        except DuplicateTemplateKeyError:
            continue
        created_count += 1

    db.commit()
    return created_count
