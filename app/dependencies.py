from uuid import UUID

from fastapi import Header, HTTPException, status

from app.constants.invoice_templates import INVOICE_TEMPLATE_DIR
from app.services.pdf_service import PdfService


def get_device_id(x_device_id: str | None = Header(default=None)) -> str:
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-Id header is required",
        )

    try:
        return str(UUID(x_device_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-Id header must be a valid UUID",
        ) from exc


def get_pdf_service() -> PdfService:
    return PdfService(templates_dir=INVOICE_TEMPLATE_DIR)
