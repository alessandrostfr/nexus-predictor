"""API tests for Block 3 artist enrichment foundation."""

from fastapi.testclient import TestClient

from app.core.paths import ARTIST_PROFILE_CACHE_PATH
from app.main import app

client = TestClient(app)


def test_artist_profile_endpoint_returns_cached_and_base_fields() -> None:
    """An artist profile should merge SQLite seed data with local enrichment cache."""
    response = client.get("/api/artist-profiles/angerfist")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "angerfist"
    assert body["data"]["name"] == "Angerfist"
    assert body["data"]["primary_genre_seed"] == "Hardcore"
    assert body["data"]["appearance_count"] >= 5
    assert body["data"]["bio"] is not None
    assert isinstance(body["data"]["top_tracks"], list)
    assert isinstance(body["data"]["latest_releases"], list)


def test_artist_profiles_list_can_filter_by_year_and_query() -> None:
    """Profile listing should keep the filters added in the backend foundation."""
    response = client.get("/api/artist-profiles?year=2026&q=project&limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 1
    assert any(item["slug"] == "project-one" for item in body["data"]["items"])


def test_artist_profile_refresh_without_external_apis_is_safe() -> None:
    """Refreshing without external APIs should materialize cache data without network calls."""
    response = client.post("/api/artist-profiles/project-one/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "project-one"
    assert body["data"]["external_calls_enabled"] is False
    assert body["data"]["refreshed"] is False
    assert len(body["data"]["warnings"]) >= 1


def test_unknown_artist_profile_returns_404() -> None:
    """Unknown artist profiles should return a controlled 404."""
    response = client.get("/api/artist-profiles/not-a-real-artist")

    assert response.status_code == 404


def test_artist_profile_cache_file_exists() -> None:
    """The local enrichment cache should be versioned for Block 3."""
    assert ARTIST_PROFILE_CACHE_PATH.exists()
