"""API tests for Block 5 predictive scoring."""

from fastapi.testclient import TestClient

from app.core.paths import PREDICTIONS_DIR
from app.main import app

client = TestClient(app)


def test_2026_prediction_endpoint_returns_attendance_range() -> None:
    """The edition prediction endpoint should return attendance range and top artists."""
    response = client.get("/api/predictions/2026")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["year"] == 2026
    assert body["data"]["attendance"]["predicted_low"] > 0
    assert body["data"]["attendance"]["predicted_mid"] >= body["data"]["attendance"]["predicted_low"]
    assert body["data"]["attendance"]["predicted_high"] >= body["data"]["attendance"]["predicted_mid"]
    assert len(body["data"]["top_artist_predictions"]) >= 5


def test_artist_demand_ranking_contains_interpretable_factors() -> None:
    """Artist demand ranking should be sorted and explainable."""
    response = client.get("/api/predictions/2026/artists?limit=20")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 20
    assert items[0]["rank"] == 1
    assert items[0]["demand_score"] >= items[-1]["demand_score"]
    assert len(items[0]["factors"]) >= 5


def test_artist_prediction_project_one_has_high_demand_context() -> None:
    """Project One should receive a high score from manual hype and special project logic."""
    response = client.get("/api/predictions/2026/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "project-one"
    assert body["data"]["main_genre"] == "Classic / Legacy Hardstyle"
    assert body["data"]["demand_score"] >= 60
    assert body["data"]["crowd_risk"] in {"high", "very_high"}
    factor_keys = {factor["key"] for factor in body["data"]["factors"]}
    assert "manual_hype_signal" in factor_keys


def test_artist_prediction_can_filter_by_genre() -> None:
    """Prediction ranking should keep Block 4 subgenre filters."""
    response = client.get("/api/predictions/2026/artists?genre=Rawstyle&limit=100")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 3
    assert all(item["main_genre"] == "Rawstyle" for item in body["data"]["items"])


def test_prediction_data_folder_exists() -> None:
    """Prediction snapshots should have a versioned data folder."""
    assert PREDICTIONS_DIR.exists()
