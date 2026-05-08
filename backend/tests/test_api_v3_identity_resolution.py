"""API tests for V3.3 artist identity resolution."""

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.db.database import SessionLocal, engine
from app.db.models import ArtistIdentityCandidateModel, ArtistIdentityLinkModel, ArtistMasterModel
from app.main import app
from app.services.identity_resolution_service import normalize_artist_name

client = TestClient(app)

EXPECTED_TABLES = {
    "artist_master",
    "artist_aliases",
    "artist_identity_links",
    "artist_identity_candidates",
}


def test_v3_identity_tables_exist_after_migration() -> None:
    """The V3.3 migration must create the identity-resolution table set."""
    table_names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(table_names)


def test_v3_identity_rebuild_creates_canonical_artists_and_aliases() -> None:
    """Rebuild should materialize canonical artists from the current seed data."""
    response = client.post("/api/v3/identity/rebuild?reset=true")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["masters_created"] > 0
    assert data["aliases_created"] >= data["masters_created"]
    assert data["links_created"] >= data["masters_created"]
    assert "high" in data["minimum_feature_confidence"]


def test_v3_identity_coverage_blocks_low_confidence_feature_links() -> None:
    """Low or pending profile matches must not feed future ML features."""
    client.post("/api/v3/identity/rebuild?reset=true")
    response = client.get("/api/v3/identity/coverage")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["ready"] is True
    assert data["masters"] > 0
    assert data["feature_eligible_links"] >= data["masters"]
    assert data["low_confidence_feature_links"] == 0
    assert set(data["minimum_feature_confidence"]) == {"high", "verified"}


def test_v3_identity_artist_detail_contains_aliases_and_links() -> None:
    """A canonical artist should expose aliases and identity links."""
    client.post("/api/v3/identity/rebuild?reset=true")
    artists = client.get("/api/v3/identity/artists?q=angerfist&limit=1")
    assert artists.status_code == 200
    items = artists.json()["data"]["items"]
    assert items

    detail = client.get(f"/api/v3/identity/artists/{items[0]['canonical_artist_key']}")
    assert detail.status_code == 200
    data = detail.json()["data"]

    assert data["display_name"]
    assert data["aliases"]
    assert data["links"]
    assert any(link["platform"] == "nexus_seed" and link["is_feature_eligible"] for link in data["links"])


def test_v3_identity_admin_review_can_verify_and_reject_candidates() -> None:
    """Admin review must be able to verify or reject ambiguous candidates."""
    client.post("/api/v3/identity/rebuild?reset=true")
    with SessionLocal() as db:
        master = db.scalar(select(ArtistMasterModel).where(ArtistMasterModel.canonical_artist_key == "angerfist"))
        if master is None:
            master = db.scalar(select(ArtistMasterModel).order_by(ArtistMasterModel.id))
        assert master is not None
        candidate = ArtistIdentityCandidateModel(
            artist_master_id=master.id,
            artist_id=master.artist_id,
            canonical_artist_key=master.canonical_artist_key,
            candidate_key=f"pytest:{master.canonical_artist_key}:candidate-review",
            platform="manual_test",
            candidate_name=master.display_name,
            normalized_candidate_name=normalize_artist_name(master.display_name),
            candidate_url="https://example.invalid/pytest-candidate",
            external_id="pytest-candidate",
            match_score=1.0,
            confidence="medium",
            status="pending_review",
            suggested_action="manual_review",
            match_method="pytest_insert",
            evidence_payload={"purpose": "test admin review"},
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        candidate_id = candidate.id

    verified = client.post(
        f"/api/v3/identity/candidates/{candidate_id}/review",
        json={"decision": "verified", "confidence": "high", "reviewed_by": "pytest", "notes": "Verified in test."},
    )
    assert verified.status_code == 200
    verified_data = verified.json()["data"]
    assert verified_data["created_link"] is not None
    assert verified_data["feature_eligible"] is True

    with SessionLocal() as db:
        created_link = db.scalar(
            select(ArtistIdentityLinkModel).where(
                ArtistIdentityLinkModel.platform == "manual_test",
                ArtistIdentityLinkModel.external_id == "pytest-candidate",
            )
        )
        assert created_link is not None
        assert created_link.match_status == "verified"
        assert created_link.is_feature_eligible is True


def test_v3_identity_conventions_are_explicit() -> None:
    """The API should document confidence gates for future feature builders."""
    response = client.get("/api/v3/identity/conventions")
    assert response.status_code == 200
    data = response.json()["data"]

    assert "verified" in data["confidence"]["allowed_values"]
    assert "pending_review" in data["match_status"]["allowed_values"]
    assert data["minimum_feature_confidence"] == ["high", "verified"]
    assert "feature" in data["feature_eligibility"]["description"].lower()
