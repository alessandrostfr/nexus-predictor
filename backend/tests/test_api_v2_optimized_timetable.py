"""API tests for V2.9 optimized timetable variants."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def rebuild_optimized_timetables() -> None:
    """Keep V2.9 tests deterministic and independent from execution order."""
    response = client.post("/api/optimized-timetables/2026/rebuild?reset=true")
    assert response.status_code == 200


def test_optimized_timetable_rebuild_generates_three_variants() -> None:
    """V2.9 should generate the three required roadmap variants."""
    response = client.post("/api/optimized-timetables/2026/rebuild?reset=true")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["variants"] == 3
    assert set(data["variant_keys"]) == {"anti_crowding_extreme", "balanced", "fan_experience"}
    assert data["slots"] >= 60
    assert data["official_available"] is False
    assert data["source_status"] == "no_official_timetable_yet"
    assert data["model_version"] == "v2.9-optimized-timetable-variants"


def test_optimized_timetable_coverage_and_comparison_are_comparable() -> None:
    """Coverage and comparison should expose comparable metrics per variant."""
    coverage = client.get("/api/optimized-timetables/2026/coverage")
    assert coverage.status_code == 200
    coverage_data = coverage.json()["data"]
    assert coverage_data["generated_variants"] == 3
    assert all(coverage_data["slots_per_variant"][key] > 0 for key in coverage_data["variant_keys"])

    comparison = client.get("/api/optimized-timetables/2026/compare")
    assert comparison.status_code == 200
    data = comparison.json()["data"]
    assert len(data["variants"]) == 3
    assert set(data["recommended_by_goal"]) == {"anti_crowding", "balanced", "fan_experience"}
    for variant in data["variants"]:
        assert {"average_crowding_score", "average_conflict_score", "average_experience_score", "average_optimization_score"}.issubset(variant)
        assert variant["average_optimization_score"] > 0


def test_optimized_variant_slots_are_non_official_and_explainable() -> None:
    """Every optimized slot must carry constraints, reasons and non-official status."""
    response = client.get("/api/optimized-timetables/2026/variants/balanced/slots?limit=30")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items
    assert all(item["is_official"] is False for item in items)
    assert all(item["official_status"] == "optimized_not_official" for item in items)
    assert all(item["reasons"] for item in items)
    assert all(item["constraints"] for item in items)
    assert {"crowding_score", "conflict_score", "experience_score", "optimization_score"}.issubset(items[0])


def test_optimized_timetable_integrity_has_no_invalid_overlaps() -> None:
    """Optimized variants must not overlap inside the same room/day or duplicate artists."""
    response = client.get("/api/optimized-timetables/2026/integrity")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is True
    assert data["expected_variants"] == 3
    assert data["generated_variants"] == 3
    assert data["missing_variants"] == []
    assert data["incomplete_slots"] == 0
    assert data["invalid_duration_slots"] == 0
    assert data["overlap_count"] == 0
    assert data["duplicate_artist_count"] == 0
    assert data["invalid_room_count"] == 0
    assert data["is_seven_room_fabrik_model"] is True


def test_optimized_timetable_filters_by_variant_room_and_artist() -> None:
    """Variant-specific lookup, aliases and artist lookup should work."""
    room_response = client.get("/api/optimized-timetables/2026/variants/fan_experience/slots?room=New%20Crystal&limit=100")
    assert room_response.status_code == 200
    room_items = room_response.json()["data"]["items"]
    assert room_items
    assert all(item["room_name"] == "Crystal Area" for item in room_items)

    artist_response = client.get("/api/optimized-timetables/2026/variants/fan_experience/artists/project-one")
    assert artist_response.status_code == 200
    data = artist_response.json()["data"]
    assert data["artist_slug"] == "project-one"
    assert data["variant_key"] == "fan_experience"
    assert data["is_official"] is False
    assert data["reasons"]
