"""API tests for Block 2 backend foundation."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_database_status() -> None:
    """The health endpoint should confirm API and SQLite readiness."""
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["database_seeded"] is True


def test_database_status_endpoint_returns_seed_counts() -> None:
    """The database endpoint should expose seed counts for local validation."""
    response = client.get("/api/database/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["editions"] == 5
    assert body["data"]["artists"] >= 100
    assert body["data"]["rooms"] >= 6


def test_editions_endpoint_returns_available_years() -> None:
    """The editions endpoint should expose all five Nexus editions."""
    response = client.get("/api/editions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert [edition["year"] for edition in body["data"]] == [2022, 2023, 2024, 2025, 2026]


def test_2026_edition_returns_normalized_lineup() -> None:
    """The 2026 edition should expose the normalized poster lineup."""
    response = client.get("/api/editions/2026")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["artist_count"] >= 60
    assert any(item["display_name"] == "Project One" for item in body["data"]["lineup"])


def test_2026_lineup_endpoint_returns_performances_only() -> None:
    """The lineup sub-endpoint should return a list of performance items."""
    response = client.get("/api/editions/2026/lineup")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 60


def test_artist_endpoint_returns_project_one_from_sqlite() -> None:
    """The artist endpoint should expose extracted artists by slug."""
    response = client.get("/api/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Project One"
    assert 2026 in body["data"]["appearance_years"]


def test_artist_list_can_filter_by_year_and_query() -> None:
    """Artist listing should support basic filters for frontend usage."""
    response = client.get("/api/artists?year=2026&q=anger&limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 1
    assert any("Angerfist" == artist["name"] for artist in body["data"]["items"])


def test_fabrik_venue_endpoint_returns_rooms() -> None:
    """The venue endpoint should expose room capacity seed data."""
    response = client.get("/api/venue/fabrik")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["rooms"]) >= 6


def test_genres_endpoint_returns_seed_distribution() -> None:
    """The genres endpoint should expose current genre seeds without classifying yet."""
    response = client.get("/api/genres")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1


def test_edition_genres_endpoint_returns_2026_distribution() -> None:
    """The edition genres endpoint should return a seed distribution for 2026."""
    response = client.get("/api/genres/editions/2026")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["year"] == 2026
    assert len(body["data"]["distribution"]) >= 1
