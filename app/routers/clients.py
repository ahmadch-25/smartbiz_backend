from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.api_response import ApiResponse
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.services import client_service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = client_service.create_client(db, payload)
    return ApiResponse(status=True, message="success", result=client)


@router.get("", response_model=ClientListResponse)
def list_clients(db: Session = Depends(get_db)):
    clients = client_service.get_clients(db)
    return ApiResponse(status=True, message="success", result=clients)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return ApiResponse(status=True, message="success", result=client)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
):
    client = client_service.update_client(db, client_id, payload)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return ApiResponse(status=True, message="success", result=client)


@router.delete(
    "/{client_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    try:
        deleted = client_service.delete_client(db, client_id)
    except client_service.ClientHasInvoicesError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return ApiResponse(
        status=True,
        message="Client deleted successfully",
        result={"id": client_id},
    )
