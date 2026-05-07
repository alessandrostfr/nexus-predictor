"""API tests for V2.5 multi-genre classification."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_multi_genre_coverage_reduces_unknown() -> None:
    """The V2.5 coverage endpoint should show a strong Unknown reduction."""
    rebuild = client.post("/api/genres/v2/rebuild?reset=true")
    assert rebuild.status_code == 200

    response = client.get("/api/genres/v2/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total_artists"] >= 100
    assert data["classified_ratio"] >= 0.75
    assert data["artists_with_secondary_genres"] > 0
    assert data["persisted_genre_rows"] >= data["total_artists"]


def test_project_one_has_main_secondary_sources_and_review_flag() -> None:
    """Project One should keep the manual override and expose V2 source metadata."""
    response = client.get("/api/genres/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["main_genre"] == "Classic / Legacy Hardstyle"
    assert "Hardstyle" in data["secondary_genres"]
    assert data["genre_confidence"] in {"high", "verified"}
    assert data["genre_sources"]
    assert data["artist_kind"] == "duo_project"
    assert data["needs_manual_review"] is True


def test_secondary_genre_filter_finds_hardstyle_children() -> None:
    """The artist list endpoint should filter by secondary genre chips."""
    response = client.get("/api/genres/artists?secondary_genre=Hardstyle&limit=100")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert items
    assert all("Hardstyle" in item["secondary_genres"] for item in items)


def test_v1_v2_comparison_reports_unknown_reduction() -> None:
    """The comparison endpoint should explain how V2 improves V1 seed genres."""
    response = client.get("/api/genres/v2/comparison?limit=1000")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total"] >= 100
    assert data["unknown_reduced"] > 0
    mad_dog = next(item for item in data["items"] if item["artist_slug"] == "mad-dog")
    assert mad_dog["v1_primary_genre"] == "Unknown"
    assert mad_dog["v2_main_genre"] == "Hardcore"


def test_existing_main_genre_filter_still_works_for_2026_rawstyle() -> None:
    """Existing frontend-compatible main-genre filtering must remain stable."""
    response = client.get("/api/genres/artists?year=2026&genre=Rawstyle&limit=100")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    slugs = {item["slug"] for item in body["data"]["items"]}
    assert "sub-zero-project" in slugs
    assert "phuture-noize" in slugs
    assert all(item["main_genre"] == "Rawstyle" for item in body["data"]["items"])
