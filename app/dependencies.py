from app.services.pdf_service import PdfService


def get_pdf_service() -> PdfService:
    return PdfService(templates_dir="app/templates/invoices")
