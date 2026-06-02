from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.invoice import Invoice
from app.schemas.client import ClientCreate, ClientUpdate


class ClientHasInvoicesError(ValueError):
    pass


def create_client(db: Session, payload: ClientCreate) -> Client:
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_clients(db: Session) -> list[Client]:
    statement = select(Client).order_by(Client.id.desc())
    return list(db.scalars(statement).all())


def get_client(db: Session, client_id: int) -> Client | None:
    statement = select(Client).where(Client.id == client_id)
    return db.scalar(statement)


def update_client(db: Session, client_id: int, payload: ClientUpdate) -> Client | None:
    client = get_client(db, client_id)
    if client is None:
        return None

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return client


def delete_client(db: Session, client_id: int) -> bool:
    client = get_client(db, client_id)
    if client is None:
        return False

    invoice_count = db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.client_id == client_id)
    )
    if invoice_count:
        raise ClientHasInvoicesError("Client has invoices and cannot be deleted")

    db.delete(client)
    db.commit()
    return True
