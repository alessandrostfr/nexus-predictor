"""Tests for V2.3 external ingestion."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_external_ingestion_run_is_safe_and_traceable() -> None:
    """The API validation hook should run the deterministic ingestion service."""
    response = client.post("/api/ingestion/external/run?reset=true&limit_artists=5")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["sources"] >= 3
    assert body["data"]["venue_prestige_items"] >= 5
    assert body["data"]["career_events"] >= 5
    assert body["data"]["skipped_unknown_artists"] == 0


def test_external_ingestion_coverage_is_available() -> None:
    """Coverage should expose source, evidence, event and artist counts."""
    response = client.get("/api/ingestion/external/coverage")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["external_sources"] >= 3
    assert body["data"]["external_career_events"] >= 5
    assert body["data"]["artists_with_external_events"] >= 5
    assert body["data"]["venue_prestige_items"] >= 5


def test_external_ingestion_evidence_reaches_artist_overview() -> None:
    """V2.3 career evidence should be visible through the existing evidence API."""
    client.post("/api/ingestion/external/run?reset=true&limit_artists=5")
    response = client.get("/api/evidence/artists/angerfist?limit=200")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    metric_keys = {metric["metric_key"] for metric in body["data"]["metrics"]}
    evidence_keys = {item["metric_key"] for item in body["data"]["evidence_items"]}

    assert "external.career_event_count" in metric_keys
    assert "external.career_event" in evidence_keys
