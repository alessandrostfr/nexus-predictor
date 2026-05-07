"""API tests for V2.7 demand model."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_v2_demand_model_rebuild_and_coverage() -> None:
    """The V2.7 model should rebuild and expose coverage counters."""
    rebuild = client.post("/api/predictions/v2/2026/rebuild?reset=true")
    assert rebuild.status_code == 200
    rebuild_body = rebuild.json()
    assert rebuild_body["success"] is True
    assert rebuild_body["data"]["predictions"] >= 20
    assert rebuild_body["data"]["model_version"] == "v2.7-interpretable-feature-model"

    coverage = client.get("/api/predictions/v2/2026/coverage")
    assert coverage.status_code == 200
    data = coverage.json()["data"]
    assert data["persisted_predictions"] == rebuild_body["data"]["predictions"]
    assert data["total_artists"] >= 20
    assert data["fallback_predictions"] < data["persisted_predictions"]


def test_v2_ranking_has_separated_scores_and_explanations() -> None:
    """V2 ranking rows must include separated score components and explanations."""
    response = client.get("/api/predictions/v2/2026/artists?limit=20")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 20
    assert items[0]["rank"] == 1
    assert items[0]["demand_score"] >= items[-1]["demand_score"]
    assert {"popularity_score", "career_score", "momentum_score", "nexus_affinity_score"}.issubset(items[0])
    assert items[0]["features"]
    assert items[0]["factors"]
    assert items[0]["explanations"]


def test_project_one_keeps_strong_v2_demand_context() -> None:
    """Project One should remain a high-interest act in the V2.7 model."""
    response = client.get("/api/predictions/v2/2026/artists/project-one")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["artist_slug"] == "project-one"
    assert data["main_genre"] == "Classic / Legacy Hardstyle"
    assert data["demand_score"] >= 55
    assert data["crowd_risk"] in {"medium", "high", "very_high"}
    feature_keys = {feature["key"] for feature in data["features"]}
    assert "genre_fit" in feature_keys
    assert "current_lineup_presence" in feature_keys


def test_v2_predictions_can_filter_by_genre() -> None:
    """V2 endpoint should preserve main-genre filtering for later frontend use."""
    response = client.get("/api/predictions/v2/2026/artists?genre=Rawstyle&limit=100")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items
    assert all(item["main_genre"] == "Rawstyle" for item in items)


def test_v1_v2_comparison_is_available() -> None:
    """V2.7 should expose a V1/V2 comparison to support model review."""
    response = client.get("/api/predictions/v2/2026/comparison?limit=25")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total"] >= 20
    assert data["items"]
    assert {"v1_demand_score", "v2_demand_score", "delta", "main_reason"}.issubset(data["items"][0])
