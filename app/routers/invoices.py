from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.params import Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_device_id, get_pdf_service
from app.schemas.api_response import ApiResponse
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.schemas.payment_record import (
    PaymentRecordCreate,
    PaymentRecordListResponse,
    PaymentRecordResponse,
)
from app.services import invoice_service, payment_service
from app.services.pdf_service import PdfService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    try:
        invoice = invoice_service.create_invoice(db, payload, device_id)
    except invoice_service.ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except invoice_service.InvalidInvoiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ApiResponse(status=True, message="success", result=invoice)


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    invoices = invoice_service.get_invoices(db, device_id)
    return ApiResponse(status=True, message="success", result=invoices)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    invoice = invoice_service.get_invoice_with_details(db, invoice_id, device_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return ApiResponse(status=True, message="success", result=invoice)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    try:
        invoice = invoice_service.update_invoice(db, invoice_id, payload, device_id)
    except invoice_service.InvalidInvoiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return ApiResponse(status=True, message="success", result=invoice)


@router.delete(
    "/{invoice_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    deleted = invoice_service.delete_invoice(db, invoice_id, device_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    return ApiResponse(
        status=True,
        message="Invoice deleted successfully",
        result={"id": invoice_id},
    )


@router.post(
    "/{invoice_id}/payments",
    response_model=PaymentRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_payment(
    invoice_id: int,
    payload: PaymentRecordCreate,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    try:
        payment = payment_service.create_payment(
            db, payload, device_id, invoice_id=invoice_id
        )
    except invoice_service.InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ApiResponse(status=True, message="success", result=payment)


@router.get("/{invoice_id}/payments", response_model=PaymentRecordListResponse)
def list_invoice_payments(
    invoice_id: int,
    db: Session = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    try:
        payments = payment_service.get_invoice_payments(db, invoice_id, device_id)
    except invoice_service.InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ApiResponse(status=True, message="success", result=payments)


@router.get("/{invoice_id}/preview-pdf")
def preview_invoice_pdf(
    invoice_id: int,
    template_key: Annotated[str, Query()],
    db: Session = Depends(get_db),
    pdf_service: PdfService = Depends(get_pdf_service),
    device_id: str = Depends(get_device_id),
):
    invoice = invoice_service.get_invoice_with_details(db, invoice_id, device_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found.",
        )

    try:
        pdf_bytes = pdf_service.generate_invoice_pdf(
            invoice=invoice,
            template_key=template_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    filename = f"invoice_{invoice.invoice_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
