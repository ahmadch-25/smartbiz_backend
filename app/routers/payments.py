from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.api_response import ApiResponse
from app.schemas.payment_record import (
    PaymentRecordCreate,
    PaymentRecordListResponse,
    PaymentRecordResponse,
)
from app.services import invoice_service
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "", response_model=PaymentRecordResponse, status_code=status.HTTP_201_CREATED
)
def create_payment(payload: PaymentRecordCreate, db: Session = Depends(get_db)):
    try:
        payment = payment_service.create_payment(db, payload)
    except invoice_service.InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ApiResponse(status=True, message="success", result=payment)


@router.get("", response_model=PaymentRecordListResponse)
def list_payments(db: Session = Depends(get_db)):
    payments = payment_service.get_payments(db)
    return ApiResponse(status=True, message="success", result=payments)


@router.get("/{payment_id}", response_model=PaymentRecordResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = payment_service.get_payment(db, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )
    return ApiResponse(status=True, message="success", result=payment)
