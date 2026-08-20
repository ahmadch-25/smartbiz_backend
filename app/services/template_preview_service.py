from app.constants.invoice_templates import (
    TEMPLATE_PREVIEW_DIR,
    get_invoice_template_definition,
)
from app.db.database import SessionLocal
from app.models.invoice_template import InvoiceTemplate


def generate_template_preview_task(template_id: int) -> None:
    db = SessionLocal()
    try:
        template = db.get(InvoiceTemplate, template_id)
        if not template:
            return

        definition = get_invoice_template_definition(template.key)
        if definition is None:
            return

        preview_path = TEMPLATE_PREVIEW_DIR / definition.preview_filename
        if not preview_path.is_file():
            raise FileNotFoundError(
                f"Preview image does not exist for template {template.key}"
            )

        template.preview_image = definition.preview_url

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Failed to generate preview for template {template_id}: {exc}")
    finally:
        db.close()
