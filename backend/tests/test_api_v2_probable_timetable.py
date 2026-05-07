"""API tests for V2.8 probable timetable prediction."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def rebuild_probable_timetable() -> None:
    """Keep V2.8 tests deterministic and independent from execution order."""
    response = client.post("/api/probable-timetables/2026/rebuild?reset=true")
    assert response.status_code == 200


def test_probable_timetable_rebuild_and_coverage_are_non_official() -> None:
    """The V2.8 generator should build slots and never claim official status."""
    rebuild = client.post("/api/probable-timetables/2026/rebuild?reset=true")
    assert rebuild.status_code == 200
    rebuild_data = rebuild.json()["data"]
    assert rebuild_data["slots"] >= 20
    assert rebuild_data["official_available"] is False
    assert rebuild_data["source_status"] == "no_official_timetable_yet"
    assert rebuild_data["model_version"] == "v2.8-probable-timetable-model"

    coverage = client.get("/api/probable-timetables/2026/coverage")
    assert coverage.status_code == 200
    data = coverage.json()["data"]
    assert data["official_available"] is False
    assert data["source_status"] == "no_official_timetable_yet"
    assert data["assigned_artists"] == rebuild_data["assigned_artists"]
    assert data["total_rooms"] <= 7
    assert data["average_probability_score"] > 0


def test_probable_timetable_slots_have_confidence_and_reasons() -> None:
    """Every V2.8 slot must be explainable and clearly predicted."""
    response = client.get("/api/probable-timetables/2026/slots?limit=30")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert items
    assert all(item["is_official"] is False for item in items)
    assert all(item["official_status"] == "predicted_not_official" for item in items)
    assert all(item["confidence"] in {"low", "medium", "medium_high", "high"} for item in items)
    assert all(item["reasons"] for item in items)
    assert {"room_name", "start_time", "end_time", "demand_score", "probability_score"}.issubset(items[0])


def test_probable_timetable_uses_real_fabrik_room_model() -> None:
    """V2.8 must stay inside the verified seven-room Fabrik room model."""
    response = client.get("/api/probable-timetables/2026")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["official_available"] is False
    assert data["room_count"] <= 7
    rooms = {room["room_name"] for room in data["rooms"]}
    assert rooms.issubset(
        {
            "Area 19",
            "Club Area",
            "Crystal Area",
            "Hangar",
            "Main Room",
            "Open Air",
            "Satelite",
        }
    )
    assert any("not an official" in note.lower() for note in data["notes"])


def test_probable_timetable_integrity_has_no_impossible_overlaps() -> None:
    """Generated room/day slots should not overlap or duplicate artists."""
    response = client.get("/api/probable-timetables/2026/integrity")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is True
    assert data["incomplete_slots"] == 0
    assert data["invalid_duration_slots"] == 0
    assert data["overlap_count"] == 0
    assert data["duplicate_artist_count"] == 0
    assert data["invalid_room_count"] == 0
    assert data["capacity_pressure_violations"] == 0
    assert data["is_seven_room_fabrik_model"] is True


def test_probable_timetable_filters_by_room_and_artist() -> None:
    """Room aliases and artist-specific lookup should work for the frontend."""
    room_response = client.get("/api/probable-timetables/2026/slots?room=New%20Crystal&limit=100")
    assert room_response.status_code == 200
    room_items = room_response.json()["data"]["items"]
    assert room_items
    assert all(item["room_name"] == "Crystal Area" for item in room_items)

    project_one = client.get("/api/probable-timetables/2026/artists/project-one")
    assert project_one.status_code == 200
    data = project_one.json()["data"]
    assert data["artist_slug"] == "project-one"
    assert data["is_official"] is False
    assert data["reasons"]
    assert data["main_genre"] == "Classic / Legacy Hardstyle"
