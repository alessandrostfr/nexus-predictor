"""Validate the V3.3 artist identity-resolution layer.

Run from the repository root after applying V3.3 and migrations:

    python backend/scripts/check_v3_identity_resolution.py

The script validates tables, rebuilds the identity layer, checks that low or
pending matches are not feature-eligible and exercises the admin review endpoint.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import inspect, select  # noqa: E402

from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.models import ArtistIdentityCandidateModel, ArtistMasterModel  # noqa: E402
from app.main import app  # noqa: E402
from app.services.identity_resolution_service import normalize_artist_name  # noqa: E402

EXPECTED_BRANCH = "refactor/v3-ml-first"
EXPECTED_TABLES = {
    "artist_master",
    "artist_aliases",
    "artist_identity_links",
    "artist_identity_candidates",
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
    """Run V3.3 identity-resolution checks."""
    print("Nexus Predictor V3.3 identity resolution validation")
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
        raise AssertionError(f"Missing V3.3 tables: {sorted(missing)}. Run: cd backend && alembic upgrade head")
    print("OK  V3.3 identity tables exist")

    client = TestClient(app)
    rebuild = client.post("/api/v3/identity/rebuild?reset=true")
    if rebuild.status_code != 200:
        raise AssertionError(f"Rebuild endpoint failed with HTTP {rebuild.status_code}: {rebuild.text}")
    rebuild_data = rebuild.json()["data"]
    if rebuild_data["masters_created"] <= 0:
        raise AssertionError("No canonical artists were created.")
    if rebuild_data["aliases_created"] < rebuild_data["masters_created"]:
        raise AssertionError("Expected at least one alias per canonical artist.")
    print("OK  rebuild endpoint creates canonical artists and aliases")

    coverage = client.get("/api/v3/identity/coverage")
    if coverage.status_code != 200:
        raise AssertionError(f"Coverage endpoint failed with HTTP {coverage.status_code}: {coverage.text}")
    coverage_data = coverage.json()["data"]
    if coverage_data["low_confidence_feature_links"] != 0:
        raise AssertionError("Low-confidence links must not be feature eligible.")
    if "high" not in coverage_data["minimum_feature_confidence"]:
        raise AssertionError("Expected high confidence as minimum feature gate.")
    print("OK  coverage endpoint enforces confidence feature gates")

    artists = client.get("/api/v3/identity/artists?limit=5")
    if artists.status_code != 200 or not artists.json()["data"]["items"]:
        raise AssertionError("Artist list endpoint did not return canonical artists.")
    first_artist = artists.json()["data"]["items"][0]["canonical_artist_key"]
    detail = client.get(f"/api/v3/identity/artists/{first_artist}")
    if detail.status_code != 200:
        raise AssertionError(f"Artist detail endpoint failed for {first_artist}: {detail.text}")
    if not detail.json()["data"]["aliases"]:
        raise AssertionError("Artist detail must include aliases.")
    print("OK  canonical artist endpoints work")

    with SessionLocal() as db:
        master = db.scalar(select(ArtistMasterModel).order_by(ArtistMasterModel.id))
        if master is None:
            raise AssertionError("No artist master row exists after rebuild.")
        candidate = ArtistIdentityCandidateModel(
            artist_master_id=master.id,
            artist_id=master.artist_id,
            canonical_artist_key=master.canonical_artist_key,
            candidate_key=f"v3_check:{master.canonical_artist_key}:manual_test",
            platform="manual_test",
            candidate_name=master.display_name,
            normalized_candidate_name=normalize_artist_name(master.display_name),
            candidate_url="https://example.invalid/v3-check",
            external_id="v3-check",
            match_score=1.0,
            confidence="medium",
            status="pending_review",
            suggested_action="manual_review",
            match_method="script_inserted_check",
            evidence_payload={"purpose": "V3.3 admin review endpoint validation"},
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        candidate_id = candidate.id

    review = client.post(
        f"/api/v3/identity/candidates/{candidate_id}/review",
        json={"decision": "verified", "confidence": "high", "reviewed_by": "check_script", "notes": "Validation review."},
    )
    if review.status_code != 200:
        raise AssertionError(f"Review endpoint failed with HTTP {review.status_code}: {review.text}")
    review_data = review.json()["data"]
    if review_data["created_link"] is None or review_data["feature_eligible"] is not True:
        raise AssertionError("Verified high-confidence candidate should create a feature-eligible link.")
    print("OK  admin review endpoint can verify candidates and create eligible links")

    conventions = client.get("/api/v3/identity/conventions")
    if conventions.status_code != 200:
        raise AssertionError(f"Conventions endpoint failed with HTTP {conventions.status_code}: {conventions.text}")
    if "verified" not in conventions.json()["data"]["confidence"]["allowed_values"]:
        raise AssertionError("Conventions endpoint must document verified confidence.")
    print("OK  identity conventions endpoint works")

    print("=" * 64)
    print("V3.3 identity resolution is ready.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - keep CLI validation friendly.
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
