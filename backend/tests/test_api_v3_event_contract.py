"""API tests for V3.1 continuous Nexus 2026 event contract."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_v3_event_contract_rebuild_and_endpoint_are_continuous() -> None:
    """The 2026 event must be one 18-hour continuous contract."""
    rebuild = client.post("/api/v3/events/2026/contract/rebuild?reset=true")
    assert rebuild.status_code == 200
    rebuild_data = rebuild.json()["data"]
    assert rebuild_data["duration_hours"] == 18
    assert rebuild_data["time_windows"] == 18
    assert rebuild_data["continuous_event"] is True

    response = client.get("/api/v3/events/2026/contract")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert body["success"] is True
    assert data["year"] == 2026
    assert data["duration_hours"] == 18
    assert data["duration_minutes"] == 1080
    assert data["continuous_event"] is True
    assert data["functional_day_key"] == "nexus_day"
    assert data["start_label"] == "13/06/2026 12:00"
    assert data["end_label"] == "14/06/2026 06:00"
    assert data["boundary_labels"][0] == "12:00"
    assert data["boundary_labels"][-1] == "06:00"
    assert len(data["time_windows"]) == 18


def test_v3_event_contract_windows_cross_midnight_without_day_split() -> None:
    """The hourly windows should cross midnight without becoming Friday/Saturday days."""
    response = client.get("/api/v3/events/2026/time-windows")
    assert response.status_code == 200
    windows = response.json()["data"]

    assert len(windows) == 18
    assert windows[0]["start_time"] == "12:00"
    assert windows[-1]["end_time"] == "06:00"
    assert all(window["functional_day_key"] == "nexus_day" for window in windows)
    assert not any(window["functional_day_key"] in {"friday", "saturday"} for window in windows)
    assert any(window["start_time"] == "23:00" and window["end_time"] == "00:00" and window["crosses_midnight"] for window in windows)
    assert all(window["duration_minutes"] == 60 for window in windows)


def test_v3_event_contract_peak_windows_are_evidence_not_labels() -> None:
    """Peak windows can exist only as evidence metadata at this stage."""
    response = client.get("/api/v3/events/2026/contract")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["peak_windows"]
    assert all(item["used_as"] == "feature_candidate_not_label" for item in data["peak_windows"])
    peak_windows = [window for window in data["time_windows"] if window["is_peak_window"]]
    assert peak_windows
    assert all(window["evidence_status"] == "manual_peak_candidate" for window in peak_windows)


def test_v3_event_contract_validation_report_passes() -> None:
    """The validation endpoint should expose the roadmap checks."""
    response = client.get("/api/v3/events/2026/contract/validation")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["valid"] is True
    assert data["duration_hours"] == 18
    assert data["time_window_count"] == 18
    assert data["contains_friday_saturday_split"] is False
    assert data["crosses_midnight"] is True
    assert data["issues"] == []
