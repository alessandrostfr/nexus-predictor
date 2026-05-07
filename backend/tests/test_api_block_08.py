"""Block 8 API tests for room capacity and timetable risk."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


EXPECTED_ROOM_SLUGS = {
    "hangar",
    "open-air",
    "main-room",
    "satelite",
    "club-area",
    "crystal-area",
    "area-19",
}


def test_room_risk_overview_returns_simulation_until_official_timetable() -> None:
    """The overview should be explicit that current values are theoretical."""
    response = client.get("/api/room-risk/2026")

    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert body["success"] is True
    assert data["year"] == 2026
    assert data["mode"] == "theoretical_simulation"
    assert data["official_timetable_available"] is False
    assert {room["slug"] for room in data["rooms"]} == EXPECTED_ROOM_SLUGS
    assert data["highest_risk_rooms"]
    assert data["heatmap"]


def test_room_risk_rooms_include_pressure_score_and_capacity() -> None:
    """Every room should expose capacity estimates and a room_pressure_score."""
    response = client.get("/api/room-risk/2026/rooms")

    assert response.status_code == 200
    rooms = response.json()["data"]
    main_room = next(room for room in rooms if room["slug"] == "main-room")

    assert main_room["estimated_capacity"] is not None
    assert main_room["room_pressure_score"] >= 0
    assert main_room["pressure_level"] in {"calm", "low", "medium", "high", "critical"}
    assert main_room["data_status"] == "theoretical_simulation"
    assert main_room["top_candidate_artists"]


def test_hotel_is_map_support_area_not_music_room() -> None:
    """The hotel is shown on the map but excluded from music room risk."""
    response = client.get("/api/room-risk/2026")

    assert response.status_code == 200
    data = response.json()["data"]

    assert "hotel-fabrik" not in {room["slug"] for room in data["rooms"]}
    hotel = next(area for area in data["venue_support_areas"] if area["slug"] == "hotel-fabrik")
    assert hotel["is_room"] is False
    assert hotel["area_type"] == "hotel"


def test_room_risk_detail_returns_one_room() -> None:
    """Individual room endpoint should work for interactive frontend cards."""
    response = client.get("/api/room-risk/2026/rooms/hangar")

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["slug"] == "hangar"
    assert data["name"] == "Hangar"
    assert data["candidate_genres"]


def test_timetable_status_exposes_import_contract() -> None:
    """The timetable endpoint should be ready for future official slots."""
    response = client.get("/api/room-risk/2026/timetable")

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["official_available"] is False
    assert data["source_status"] == "no_official_timetable_yet"
    assert data["slots"] == []
    assert "room_slug" in data["import_contract"]
