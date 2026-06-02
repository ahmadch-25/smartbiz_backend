# # app/services/template_preview_service.py

# from app.constants.dummy_template_context import SAMPLE_PREVIEW_CONTEXT
from app.db.database import SessionLocal
from app.models.invoice_template import InvoiceTemplate
# import pymupdf
# from pathlib import Path
# from jinja2 import Environment, FileSystemLoader, select_autoescape
# from weasyprint import HTML

# TEMPLATE_FILES = {
#     "modern_1": "modern_1.html",
#     "minimal_1": "minimal_1.html",
#     "corporate_1": "corporate_1.html",
# }

# TEMPLATES_DIR = Path("app/templates/invoices")
# PREVIEW_OUTPUT_DIR = Path("app/static/template_previews")
# PREVIEW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# class TemplatePreviewGenerationError(Exception):
#     pass


# def generate_template_preview_file(template_key: str) -> str:
#     if template_key not in TEMPLATE_FILES:
#         raise TemplatePreviewGenerationError(f"Unknown template key: {template_key}")

#     template_file = TEMPLATE_FILES[template_key]

#     env = Environment(
#         loader=FileSystemLoader(str(TEMPLATES_DIR)),
#         autoescape=select_autoescape(["html", "xml"]),
#     )

#     template = env.get_template(template_file)
#     rendered_html = template.render(**SAMPLE_PREVIEW_CONTEXT)

#     pdf_bytes = HTML(
#         string=rendered_html,
#         base_url=str(TEMPLATES_DIR),
#     ).write_pdf()

#     preview_filename = f"{template_key}.png"
#     preview_path = PREVIEW_OUTPUT_DIR / preview_filename

#     pdf_doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
#     try:
#         first_page = pdf_doc[0]
#         pix = first_page.get_pixmap(
#             matrix=pymupdf.Matrix(1.5, 1.5),
#             alpha=False,
#         )
#         pix.save(preview_path)
#     finally:
#         pdf_doc.close()

#     return f"/static/template_previews/{preview_filename}"


def generate_template_preview_task(template_id: int) -> None:
    db = SessionLocal()
    try:
        template = db.get(InvoiceTemplate, template_id)
        if not template:
            return

        preview_url = f"/static/template_previews/{template.key}.png"
        template.preview_image = preview_url

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Failed to generate preview for template {template_id}: {exc}")
    finally:
        db.close()
