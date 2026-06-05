from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.ai_invoice import AiInvoiceDraftRequest, AiInvoiceDraftResponse
from app.schemas.api_response import ApiResponse
from app.services import ai_invoice_service

router = APIRouter(prefix="/ai/invoice", tags=["AI Invoice"])


@router.post(
    "/draft",
    response_model=AiInvoiceDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_invoice_draft(
    payload: AiInvoiceDraftRequest,
    db: Session = Depends(get_db),
):
    try:
        result = ai_invoice_service.build_ai_invoice_draft(db, payload.text)
    except ai_invoice_service.AiInvoiceExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ai_invoice_service.AiInvoiceDraftError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ApiResponse(status=True, message="success", result=result)
