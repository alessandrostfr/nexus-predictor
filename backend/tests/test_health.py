"""Basic API tests for the project foundation and Block 1 dataset."""

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


def test_editions_endpoint_returns_researched_seed_files() -> None:
    """The editions endpoint should expose all five Nexus edition files."""
    response = client.get("/api/editions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 5


def test_2026_edition_contains_lineup_seed() -> None:
    """The 2026 edition should contain the extracted poster lineup."""
    response = client.get("/api/editions/2026")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["artist_count"] >= 60
    assert any(item["display_name"] == "Project One" for item in body["data"]["lineup"])


def test_fabrik_venue_endpoint_returns_rooms() -> None:
    """The venue endpoint should expose room capacity seed data."""
    response = client.get("/api/venue/fabrik")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["rooms"]) >= 6


def test_artist_index_endpoint_returns_project_one() -> None:
    """The artist endpoint should expose extracted artists by slug."""
    response = client.get("/api/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Project One"
