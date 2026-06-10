from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.database import get_db
from app.main import app as fastapi_app
from app.models.client import Client

DEVICE_A = "11111111-1111-1111-1111-111111111111"
DEVICE_B = "22222222-2222-2222-2222-222222222222"
fastapi_application = fastapi_app


def make_test_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    fastapi_application.dependency_overrides[get_db] = override_get_db
    return TestClient(
        fastapi_application, raise_server_exceptions=False
    ), testing_session


def clear_overrides() -> None:
    fastapi_application.dependency_overrides.clear()


def test_missing_device_id_returns_400():
    client, _ = make_test_client()
    try:
        response = client.get("/clients")
        assert response.status_code == 400
        assert response.json()["message"] == "X-Device-Id header is required"
    finally:
        clear_overrides()


def test_body_device_id_cannot_override_header_value():
    client, session_factory = make_test_client()
    try:
        response = client.post(
            "/clients",
            headers={"X-Device-Id": DEVICE_A},
            json={
                "name": "Device A Client",
                "device_id": DEVICE_B,
            },
        )
        assert response.status_code == 201

        with session_factory() as db:
            saved_client = db.scalar(
                select(Client).where(Client.name == "Device A Client")
            )
            assert saved_client is not None
            assert saved_client.device_id == DEVICE_A
    finally:
        clear_overrides()


def test_device_a_cannot_see_update_or_delete_device_b_client():
    client, _ = make_test_client()
    try:
        client_a = client.post(
            "/clients",
            headers={"X-Device-Id": DEVICE_A},
            json={"name": "A Client"},
        ).json()["result"]
        client_b = client.post(
            "/clients",
            headers={"X-Device-Id": DEVICE_B},
            json={"name": "B Client"},
        ).json()["result"]

        list_a = client.get("/clients", headers={"X-Device-Id": DEVICE_A})
        list_b = client.get("/clients", headers={"X-Device-Id": DEVICE_B})

        assert [row["id"] for row in list_a.json()["result"]] == [client_a["id"]]
        assert [row["id"] for row in list_b.json()["result"]] == [client_b["id"]]

        get_b_from_a = client.get(
            f"/clients/{client_b['id']}",
            headers={"X-Device-Id": DEVICE_A},
        )
        patch_b_from_a = client.patch(
            f"/clients/{client_b['id']}",
            headers={"X-Device-Id": DEVICE_A},
            json={"name": "Wrong Device Update"},
        )
        delete_b_from_a = client.delete(
            f"/clients/{client_b['id']}",
            headers={"X-Device-Id": DEVICE_A},
        )

        assert get_b_from_a.status_code == 404
        assert patch_b_from_a.status_code == 404
        assert delete_b_from_a.status_code == 404
    finally:
        clear_overrides()


def test_invoice_and_payment_cannot_use_other_device_records():
    client, _ = make_test_client()
    try:
        client_b = client.post(
            "/clients",
            headers={"X-Device-Id": DEVICE_B},
            json={"name": "B Client"},
        ).json()["result"]

        invoice_from_a_with_b_client = client.post(
            "/invoices",
            headers={"X-Device-Id": DEVICE_A},
            json={
                "client_id": client_b["id"],
                "issue_date": "2026-06-10",
                "due_date": "2026-06-24",
                "items": [
                    {
                        "product_name": "Soap",
                        "quantity": "1",
                        "unit_price": "100.00",
                    }
                ],
            },
        )
        assert invoice_from_a_with_b_client.status_code == 404

        invoice_b = client.post(
            "/invoices",
            headers={"X-Device-Id": DEVICE_B},
            json={
                "client_id": client_b["id"],
                "issue_date": "2026-06-10",
                "due_date": "2026-06-24",
                "items": [
                    {
                        "product_name": "Soap",
                        "quantity": "1",
                        "unit_price": "100.00",
                    }
                ],
            },
        ).json()["result"]

        payment_from_a_with_b_invoice = client.post(
            "/payments",
            headers={"X-Device-Id": DEVICE_A},
            json={
                "invoice_id": invoice_b["id"],
                "amount": "100.00",
                "payment_date": "2026-06-10",
            },
        )
        assert payment_from_a_with_b_invoice.status_code == 404
    finally:
        clear_overrides()
