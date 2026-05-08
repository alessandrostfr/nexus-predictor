"""Validate the V3.1 continuous Nexus 2026 event contract.

Run from the repository root after applying the V3.1 ZIP and migrations:

    python backend/scripts/check_v3_event_contract.py

The script checks database tables, the FastAPI contract endpoint and the public
payload constraints required by the V3 roadmap.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

from app.db.database import engine  # noqa: E402
from app.main import app  # noqa: E402

EXPECTED_BRANCH = "refactor/v3-ml-first"
EXPECTED_TABLES = {"event_contracts", "event_time_windows"}


def current_git_branch() -> str | None:
    """Return the current branch when Git is available."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    return result.stdout.strip() or None


def assert_equal(actual: object, expected: object, label: str) -> None:
    """Raise a readable assertion error when a value is wrong."""
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> int:
    """Run V3.1 contract checks."""
    print("Nexus Predictor V3.1 event contract validation")
    print("=" * 52)

    branch = current_git_branch()
    if branch is None:
        print("WARN could not read Git branch. Run inside the repository with Git installed.")
    elif branch != EXPECTED_BRANCH:
        print(f"WARN current branch is {branch!r}, expected {EXPECTED_BRANCH!r}.")
    else:
        print(f"OK  branch: {EXPECTED_BRANCH}")

    table_names = set(inspect(engine).get_table_names())
    missing = EXPECTED_TABLES - table_names
    if missing:
        raise AssertionError(f"Missing V3.1 tables: {sorted(missing)}. Run: cd backend && alembic upgrade head")
    print("OK  V3.1 tables exist")

    client = TestClient(app)
    rebuild = client.post("/api/v3/events/2026/contract/rebuild?reset=true")
    assert_equal(rebuild.status_code, 200, "rebuild status")
    print("OK  rebuild endpoint works")

    response = client.get("/api/v3/events/2026/contract")
    assert_equal(response.status_code, 200, "contract status")
    payload = response.json()["data"]

    assert_equal(payload["duration_hours"], 18, "duration_hours")
    assert_equal(payload["duration_minutes"], 1080, "duration_minutes")
    assert_equal(payload["continuous_event"], True, "continuous_event")
    assert_equal(payload["functional_day_key"], "nexus_day", "functional_day_key")
    assert_equal(payload["start_label"], "13/06/2026 12:00", "start_label")
    assert_equal(payload["end_label"], "14/06/2026 06:00", "end_label")
    assert_equal(len(payload["time_windows"]), 18, "time_windows length")
    assert_equal(payload["boundary_labels"][0], "12:00", "first boundary")
    assert_equal(payload["boundary_labels"][-1], "06:00", "last boundary")

    forbidden = {"friday", "saturday"}
    functional_keys = {window["functional_day_key"].lower() for window in payload["time_windows"]}
    if functional_keys & forbidden:
        raise AssertionError(f"2026 contract still contains Friday/Saturday split: {functional_keys & forbidden}")
    if not any(window["crosses_midnight"] for window in payload["time_windows"]):
        raise AssertionError("No time window crosses midnight; expected 23:00-00:00 to cross.")
    if not any(window["is_peak_window"] and window["evidence_status"] == "manual_peak_candidate" for window in payload["time_windows"]):
        raise AssertionError("Peak candidate windows must be registered as evidence metadata.")
    print("OK  contract payload is continuous and crosses midnight")

    validation = client.get("/api/v3/events/2026/contract/validation")
    assert_equal(validation.status_code, 200, "validation status")
    validation_payload = validation.json()["data"]
    assert_equal(validation_payload["valid"], True, "validation report")
    assert_equal(validation_payload["contains_friday_saturday_split"], False, "no day split")
    print("OK  validation endpoint passes")

    print("=" * 52)
    print("V3.1 event contract is ready.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - keep CLI validation friendly.
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
