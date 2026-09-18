from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_status_returns_expected_shape() -> None:
    response = client.get("/api/status")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert body["environment"]
    assert body["version"]
    assert "timestamp" in body


def test_status_cors_headers_present_for_allowed_origin() -> None:
    response = client.get(
        "/api/status",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
