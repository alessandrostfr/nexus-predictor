"""API tests for Nexus Predictor V2.2 Spotify integration.

The tests intentionally avoid real Spotify calls. They validate that the route
surface exists, that missing credentials fail safely and that cache reads are
controlled.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_spotify_status_is_safe_without_exposing_secrets() -> None:
    """The status endpoint should never expose client secret values."""
    response = client.get("/api/spotify/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "configured" in body["data"]
    assert "client_secret" not in str(body).lower()
    assert "credentials_hint" in body["data"]


def test_spotify_cache_endpoint_returns_controlled_response() -> None:
    """Reading cache for an artist should not require Spotify credentials."""
    response = client.get("/api/spotify/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Spotify cache" in body["message"] or "No Spotify cache" in body["message"]


def test_spotify_refresh_fails_safely_without_credentials() -> None:
    """Real refresh must fail with a clear controlled error when credentials are missing."""
    status_response = client.get("/api/spotify/status")
    if status_response.json()["data"]["configured"] is True:
        # In a real credentialed local environment the endpoint may perform a
        # network call, so this no-credential assertion is skipped naturally.
        return

    response = client.post("/api/spotify/artists/project-one/refresh?force=true")

    assert response.status_code == 503
    assert "Spotify credentials are missing" in response.text


def test_spotify_routes_are_visible_in_openapi_schema() -> None:
    """Swagger/OpenAPI should expose the new V2.2 route group."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/spotify/status" in paths
    assert "/api/spotify/artists/{artist_slug}/refresh" in paths
