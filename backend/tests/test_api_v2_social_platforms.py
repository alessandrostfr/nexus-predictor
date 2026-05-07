"""API tests for Nexus Predictor V2.4 social and music-platform ingestion."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_social_platform_status_is_safe() -> None:
    """The status endpoint should not expose API keys or secrets."""
    response = client.get("/api/social-platforms/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "lastfm" in body["data"]
    assert "api_key" not in str(body).lower()
    assert "secret" not in str(body).lower()


def test_social_platform_run_imports_manual_json_and_csv() -> None:
    """The mixed V2.4 import should create social/profile rows and metrics."""
    response = client.post("/api/social-platforms/run?reset=true")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["social_profiles"] >= 5
    assert body["data"]["platform_profiles"] >= 5
    assert body["data"]["artist_metrics"] >= 5


def test_social_platform_coverage_reports_scores() -> None:
    """Coverage should expose imported rows and score freshness."""
    client.post("/api/social-platforms/run?reset=true")
    response = client.get("/api/social-platforms/coverage")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["social_profiles"] >= 5
    assert body["data"]["platform_profiles"] >= 5
    assert body["data"]["artists_with_scores"] >= 1


def test_artist_social_overview_contains_scores_and_profiles() -> None:
    """Artist overview should include social profiles, music profiles and scores."""
    client.post("/api/social-platforms/run?reset=true")
    response = client.get("/api/social-platforms/artists/angerfist")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["artist_slug"] == "angerfist"
    assert body["data"]["social_profiles"]
    assert body["data"]["platform_profiles"]
    metric_keys = {metric["metric_key"] for metric in body["data"]["metrics"]}
    assert "social.reach_score" in metric_keys
    assert "social.engagement_score" in metric_keys
    assert "social.momentum_score" in metric_keys


def test_lastfm_refresh_without_key_fails_safely(monkeypatch) -> None:
    """Without LASTFM_API_KEY, the endpoint should fail safely without traceback."""
    monkeypatch.delenv("LASTFM_API_KEY", raising=False)
    response = client.post("/api/social-platforms/lastfm/angerfist/refresh?force=true")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["data"]["configured"] is False
    assert "api_key" not in str(body).lower()
