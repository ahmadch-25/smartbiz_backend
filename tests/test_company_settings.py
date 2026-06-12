from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.database import get_db
from app.main import app as fastapi_app
from app.models.company_settings import CompanySettings

DEVICE_A = "11111111-1111-1111-1111-111111111111"
DEVICE_B = "22222222-2222-2222-2222-222222222222"


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

    fastapi_app.dependency_overrides[get_db] = override_get_db
    return TestClient(fastapi_app, raise_server_exceptions=False), testing_session


def clear_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


def test_company_settings_requires_device_id():
    client, _ = make_test_client()
    try:
        response = client.get("/company-settings")
        assert response.status_code == 400
        assert response.json()["message"] == "X-Device-Id header is required"
    finally:
        clear_overrides()


def test_company_settings_upsert_is_scoped_by_device():
    client, _ = make_test_client()
    try:
        response_a = client.put(
            "/company-settings",
            headers={"X-Device-Id": DEVICE_A},
            json={
                "company_name": "A Company",
                "logo_url": "https://example.com/a.png",
                "address": "A Street",
                "phone": "+920000000",
                "default_currency": "pkr",
            },
        )
        response_b = client.put(
            "/company-settings",
            headers={"X-Device-Id": DEVICE_B},
            json={"company_name": "B Company"},
        )

        assert response_a.status_code == 200
        assert response_b.status_code == 200
        assert response_a.json()["result"]["default_currency"] == "PKR"

        get_a = client.get("/company-settings", headers={"X-Device-Id": DEVICE_A})
        get_b = client.get("/company-settings", headers={"X-Device-Id": DEVICE_B})

        assert get_a.json()["result"]["company_name"] == "A Company"
        assert get_b.json()["result"]["company_name"] == "B Company"

        update_a = client.put(
            "/company-settings",
            headers={"X-Device-Id": DEVICE_A},
            json={"company_name": "A Company Updated"},
        )

        assert update_a.status_code == 200
        assert update_a.json()["result"]["company_name"] == "A Company Updated"
        assert update_a.json()["result"]["address"] == "A Street"
    finally:
        clear_overrides()


def test_body_device_id_cannot_override_company_settings_header():
    client, session_factory = make_test_client()
    try:
        response = client.put(
            "/company-settings",
            headers={"X-Device-Id": DEVICE_A},
            json={
                "device_id": DEVICE_B,
                "company_name": "Header Device Company",
            },
        )

        assert response.status_code == 200

        with session_factory() as db:
            settings = db.scalar(
                select(CompanySettings).where(
                    CompanySettings.company_name == "Header Device Company"
                )
            )
            assert settings is not None
            assert settings.device_id == DEVICE_A
    finally:
        clear_overrides()
