from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.invoice_template import InvoiceTemplate
from app.schemas.invoice_template import InvoiceTemplateCreate, InvoiceTemplateUpdate


class DuplicateTemplateKeyError(ValueError):
    pass


def get_active_invoice_templates(db: Session) -> list[InvoiceTemplate]:
    statement = (
        select(InvoiceTemplate)
        .where(InvoiceTemplate.is_active.is_(True))
        .order_by(InvoiceTemplate.id.asc())
    )
    return list(db.scalars(statement).all())


def get_active_invoice_template(
    db: Session,
    template_id: int,
) -> InvoiceTemplate | None:
    statement = select(InvoiceTemplate).where(
        InvoiceTemplate.id == template_id,
        InvoiceTemplate.is_active.is_(True),
    )
    return db.scalar(statement)


def get_invoice_template_by_key(db: Session, key: str) -> InvoiceTemplate | None:
    statement = select(InvoiceTemplate).where(InvoiceTemplate.key == key)
    return db.scalar(statement)


def create_invoice_template(
    db: Session,
    payload: InvoiceTemplateCreate,
) -> InvoiceTemplate:
    if get_invoice_template_by_key(db, payload.key) is not None:
        raise DuplicateTemplateKeyError("Invoice template key already exists")

    template = InvoiceTemplate(**payload.model_dump())
    db.add(template)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateTemplateKeyError("Invoice template key already exists") from exc

    db.refresh(template)
    return template


def update_invoice_template(
    db: Session,
    template_id: int,
    payload: InvoiceTemplateUpdate,
) -> InvoiceTemplate | None:
    template = get_active_invoice_template(db, template_id)
    if template is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


def soft_delete_invoice_template(db: Session, template_id: int) -> bool:
    template = get_active_invoice_template(db, template_id)
    if template is None:
        return False

    # template.is_active = False
    db.delete(template)
    db.commit()
    return True
