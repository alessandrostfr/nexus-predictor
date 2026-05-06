"""Basic API tests for Block 0."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_success() -> None:
    """The health endpoint should confirm that the API is alive."""
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_editions_endpoint_returns_seed_files() -> None:
    """The editions endpoint should expose the placeholder dataset files."""
    response = client.get("/api/editions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 5
