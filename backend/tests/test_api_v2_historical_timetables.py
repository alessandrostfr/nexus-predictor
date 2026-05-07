"""API tests for V2.6 historical timetable dataset."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def rebuild_historical_timetable_seed() -> None:
    """Keep V2.6 tests deterministic even when run individually."""
    response = client.post("/api/historical-timetables/import?reset=true")
    assert response.status_code == 200


def test_historical_timetable_import_and_coverage() -> None:
    """The V2.6 import should persist 2022-2025 slots and coverage counters."""
    imported = client.post("/api/historical-timetables/import?reset=true")
    assert imported.status_code == 200
    imported_body = imported.json()
    assert imported_body["success"] is True
    assert imported_body["data"]["slots"] >= 200

    response = client.get("/api/historical-timetables/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["years"] == [2022, 2023, 2024, 2025]
    assert data["total_days"] == 6
    assert data["slots_with_artist_slug"] == data["total_slots"]
    assert data["slots_with_source"] == data["total_slots"]
    assert data["year_2025_is_seven_room_model"] is True


def test_historical_timetable_2025_uses_seven_real_rooms() -> None:
    """The 2025 correction must model seven real Fabrik rooms, not thirteen stages."""
    response = client.get("/api/historical-timetables/2025")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["room_count"] == 7
    assert len(data["days"]) == 2
    rooms = {room["room_name"] for room in data["rooms"]}
    assert rooms == {
        "Area 19",
        "Club Area",
        "Crystal Area",
        "Hangar",
        "Main Room",
        "Open Air",
        "Satelite",
    }


def test_historical_timetable_room_aliases_are_normalized() -> None:
    """Historical aliases such as New Crystal and Rave Area Club should normalize."""
    crystal = client.get("/api/historical-timetables/2025/slots?room=New%20Crystal&limit=100")
    assert crystal.status_code == 200
    crystal_items = crystal.json()["data"]["items"]
    assert crystal_items
    assert all(item["room_name"] == "Crystal Area" for item in crystal_items)

    rave_area = client.get("/api/historical-timetables/2025/slots?room=Rave%20Area%20Club&limit=100")
    assert rave_area.status_code == 200
    rave_items = rave_area.json()["data"]["items"]
    assert rave_items
    assert all(item["room_name"] == "Club Area" for item in rave_items)


def test_historical_timetable_integrity_has_no_impossible_overlaps() -> None:
    """Slots should be complete and should not overlap inside the same room/day."""
    response = client.get("/api/historical-timetables/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["valid"] is True
    assert data["incomplete_slots"] == 0
    assert data["invalid_duration_slots"] == 0
    assert data["overlap_count"] == 0
    assert data["year_2025_is_seven_room_model"] is True


def test_historical_timetable_artist_and_headliner_filters_work() -> None:
    """The API should filter by artist and expose headliner slot flags."""
    artist_response = client.get("/api/historical-timetables/slots?artist_slug=angerfist&limit=100")
    assert artist_response.status_code == 200
    artist_items = artist_response.json()["data"]["items"]
    assert artist_items
    assert all(item["artist_slug"] == "angerfist" for item in artist_items)

    headliner_response = client.get("/api/historical-timetables/2025/slots?only_headliners=true&limit=200")
    assert headliner_response.status_code == 200
    headliner_items = headliner_response.json()["data"]["items"]
    assert headliner_items
    assert all(item["is_headliner_slot"] is True for item in headliner_items)
