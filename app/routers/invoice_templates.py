from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.constants.dummy_template_context import SAMPLE_PREVIEW_CONTEXT
from app.constants.invoice_templates import (
    INVOICE_TEMPLATE_DIR,
    INVOICE_TEMPLATE_FILES,
)
from app.db.database import get_db
from app.schemas.invoice_template import (
    ApiResponse,
    InvoiceTemplateCreate,
    InvoiceTemplateListResponse,
    InvoiceTemplateOut,
    InvoiceTemplateResponse,
    InvoiceTemplateUpdate,
)
from app.services import invoice_template_service
from app.services.template_preview_service import generate_template_preview_task


router = APIRouter(prefix="/invoice-templates", tags=["Invoice Templates"])

TEMPLATE_FILES = INVOICE_TEMPLATE_FILES
PREVIEW_ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(INVOICE_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def build_invoice_template_response(template, request: Request) -> InvoiceTemplateOut:
    preview_image = None
    if template.preview_image:
        if template.preview_image.startswith("/static/"):
            static_path = template.preview_image.removeprefix("/static/")
            preview_image = str(request.url_for("static", path=static_path))
        else:
            preview_image = template.preview_image

    return InvoiceTemplateOut(
        id=template.id,
        name=template.name,
        key=template.key,
        description=template.description,
        preview_image=preview_image,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("", response_model=InvoiceTemplateListResponse)
def list_invoice_templates(request: Request, db: Session = Depends(get_db)):
    templates = invoice_template_service.get_active_invoice_templates(db)
    result = [
        build_invoice_template_response(template, request) for template in templates
    ]
    return ApiResponse(status=True, message="success", result=result)


@router.get("/preview/{template_key}", response_class=HTMLResponse)
def preview_invoice_template(template_key: str):
    template_file = TEMPLATE_FILES.get(template_key)
    if template_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice template preview not found",
        )

    template = PREVIEW_ENVIRONMENT.get_template(template_file)
    return HTMLResponse(template.render(**SAMPLE_PREVIEW_CONTEXT))


@router.get("/{template_id}", response_model=InvoiceTemplateResponse)
def get_invoice_template(template_id: int, db: Session = Depends(get_db)):
    template = invoice_template_service.get_active_invoice_template(db, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice template not found",
        )
    return ApiResponse(status=True, message="success", result=template)


@router.post(
    "",
    response_model=InvoiceTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_template(
    payload: InvoiceTemplateCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        template = invoice_template_service.create_invoice_template(db, payload)
    except invoice_template_service.DuplicateTemplateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    background_tasks.add_task(generate_template_preview_task, template.id)
    return ApiResponse(status=True, message="success", result=template)


@router.patch("/{template_id}", response_model=InvoiceTemplateResponse)
def update_invoice_template(
    template_id: int,
    payload: InvoiceTemplateUpdate,
    db: Session = Depends(get_db),
):
    template = invoice_template_service.update_invoice_template(
        db, template_id, payload
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice template not found",
        )
    return ApiResponse(status=True, message="success", result=template)


@router.delete(
    "/{template_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
)
def delete_invoice_template(template_id: int, db: Session = Depends(get_db)):
    deleted = invoice_template_service.soft_delete_invoice_template(db, template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice template not found",
        )
    return ApiResponse(
        status=True,
        message="Invoice template deleted successfully",
        result={"id": template_id},
    )
