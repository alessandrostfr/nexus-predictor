"""API tests for Nexus Predictor V2.1 evidence layer."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_evidence_coverage_has_v1_imported_artists() -> None:
    """The V2 evidence layer should import V1 artists and source-backed evidence."""
    response = client.get("/api/evidence/coverage")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["artists"] >= 100
    assert body["data"]["artists_with_evidence"] >= 100
    assert body["data"]["sources"] >= 5
    assert body["data"]["evidence_items"] >= 300
    assert body["data"]["artist_metrics"] >= 200


def test_sources_endpoint_exposes_manual_and_internal_sources() -> None:
    """The source registry should include internal and manual evidence sources."""
    response = client.get("/api/evidence/sources")

    assert response.status_code == 200
    body = response.json()
    keys = {source["key"] for source in body["data"]}
    assert "internal_nexus_dataset" in keys
    assert "manual_user_evidence" in keys


def test_artist_evidence_endpoint_returns_project_one_traceability() -> None:
    """Artist evidence should include atomic evidence and derived metrics."""
    response = client.get("/api/evidence/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["artist_slug"] == "project-one"
    assert len(body["data"]["evidence_items"]) >= 3
    metric_keys = {metric["metric_key"] for metric in body["data"]["metrics"]}
    assert "nexus_appearance_count" in metric_keys
    assert "v1_primary_genre_seed" in metric_keys


def test_manual_evidence_can_be_registered_for_existing_artist() -> None:
    """Manual user knowledge should be stored as verified evidence."""
    payload = {
        "artist_slug": "project-one",
        "metric_key": "manual.test_evidence_note",
        "metric_value": "Manual validation from automated test.",
        "confidence": "verified",
        "status": "confirmed",
        "notes": "This proves manual evidence can be captured with notes.",
    }
    response = client.post("/api/evidence/manual", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["artist_slug"] == "project-one"
    assert body["data"]["metric_key"] == "manual.test_evidence_note"
    assert body["data"]["confidence"] == "verified"
    assert body["data"]["extraction_method"] == "user_evidence"


def test_venue_prestige_endpoint_returns_fabrik_seed() -> None:
    """Venue prestige seed should expose Fabrik room data for future features."""
    response = client.get("/api/evidence/venue-prestige")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
