from fastapi.testclient import TestClient
from starlette.routing import Route

from app.main import app


def test_unhandled_exception_returns_standard_json_response():
    def broken_endpoint():
        raise RuntimeError("secret file path /tmp/internal.py")

    route_path = "/__test__/broken"
    if not any(
        isinstance(route, Route) and route.path == route_path for route in app.routes
    ):
        app.add_api_route(route_path, broken_endpoint, methods=["GET"])

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(route_path)

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": False,
        "message": "Internal server error",
        "result": None,
    }
    assert "internal.py" not in response.text
