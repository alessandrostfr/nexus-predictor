"""Validate the V3.2 ML-ready data foundation.

Run from the repository root after applying the V3.2 ZIP and migrations:

    python backend/scripts/check_v3_ml_data_foundation.py

The script checks database tables, the FastAPI coverage endpoints and the
roadmap conventions required before V3.3+ ingestion/ML work can begin.
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
EXPECTED_TABLES = {
    "raw_sources",
    "raw_snapshots",
    "normalized_metrics",
    "ml_datasets",
    "ml_feature_snapshots",
    "ml_labels",
    "ml_model_runs",
    "ml_predictions",
}


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


def main() -> int:
    """Run V3.2 storage and API checks."""
    print("Nexus Predictor V3.2 ML-ready data foundation validation")
    print("=" * 64)

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
        raise AssertionError(f"Missing V3.2 tables: {sorted(missing)}. Run: cd backend && alembic upgrade head")
    print("OK  V3.2 tables exist")

    client = TestClient(app)
    coverage = client.get("/api/v3/ml-data/coverage")
    if coverage.status_code != 200:
        raise AssertionError(f"Coverage endpoint failed with HTTP {coverage.status_code}: {coverage.text}")
    coverage_data = coverage.json()["data"]
    returned_tables = {item["table_name"] for item in coverage_data["tables"]}
    if returned_tables != EXPECTED_TABLES:
        raise AssertionError(f"Coverage tables mismatch: {sorted(returned_tables)}")
    if coverage_data["ready"] is not True:
        raise AssertionError("Coverage endpoint did not mark the foundation as ready.")
    print("OK  coverage endpoint returns all V3.2 tables")

    contracts = client.get("/api/v3/ml-data/contracts")
    if contracts.status_code != 200:
        raise AssertionError(f"Contracts endpoint failed with HTTP {contracts.status_code}: {contracts.text}")
    if len(contracts.json()["data"]) != len(EXPECTED_TABLES):
        raise AssertionError("Contracts endpoint does not return every V3.2 table contract.")
    print("OK  table contracts endpoint works")

    conventions = client.get("/api/v3/ml-data/conventions")
    if conventions.status_code != 200:
        raise AssertionError(f"Conventions endpoint failed with HTTP {conventions.status_code}: {conventions.text}")
    confidence_values = conventions.json()["data"]["confidence"]["allowed_values"]
    for value in ["verified", "high", "medium", "low", "rejected"]:
        if value not in confidence_values:
            raise AssertionError(f"Missing confidence convention: {value}")
    print("OK  conventions endpoint includes confidence/source rules")

    print("=" * 64)
    print("V3.2 ML-ready data foundation is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
