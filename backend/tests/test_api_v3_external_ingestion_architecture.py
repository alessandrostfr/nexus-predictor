"""Tests for V3.4-A external-ingestion architecture.

These tests must remain offline. They validate contracts, table shape, dry-run
behavior and secret-safety without making any real API calls.
"""

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, func

from app.collectors.deduplication import build_snapshot_key, content_hash
from app.collectors.registry import COLLECTOR_REGISTRY, TOOL_EVALUATION_REGISTRY
from app.db.database import engine, SessionLocal
from app.db.models import NormalizedMetricModel, RawSnapshotModel
from app.main import app

client = TestClient(app)

EXPECTED_TABLES = {"source_tool_evaluations", "collector_runs", "collector_run_items"}
EXPECTED_STATUSES = {
    "configured",
    "not_configured",
    "skipped",
    "succeeded",
    "partial",
    "failed",
    "rate_limited",
    "blocked_by_policy",
    "timeout",
    "quota_exceeded",
    "invalid_credentials",
    "not_found",
    "ambiguous_match",
    "access_unconfirmed",
    "access_unavailable",
}


def test_v3_4_a_tables_and_lineage_columns_exist() -> None:
    """The migration must create run/tool tables and extend V3.2 data tables."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(table_names)

    raw_snapshot_columns = {column["name"] for column in inspector.get_columns("raw_snapshots")}
    normalized_metric_columns = {column["name"] for column in inspector.get_columns("normalized_metrics")}

    assert {"canonical_artist_key", "collector_run_id", "collector_key", "source_reported_at", "collector_version", "normalizer_version"}.issubset(raw_snapshot_columns)
    assert {"canonical_artist_key", "collector_run_id", "collector_key", "source_reported_at", "collector_version", "normalizer_version", "metric_schema_version", "is_diagnostic_only"}.issubset(normalized_metric_columns)


def test_v3_4_a_architecture_endpoint_exposes_contracts() -> None:
    """Architecture endpoint should expose statuses and package contracts."""
    response = client.get("/api/v3/external-ingestion/architecture")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["ready"] is True
    assert data["no_external_calls_in_tests"] is True
    assert data["no_secrets_in_api"] is True
    assert data["dry_run_persists_external_data"] is False
    assert EXPECTED_STATUSES.issubset(set(data["statuses"]))
    assert "backend/app/collectors/deduplication.py" in data["collector_package"]


def test_v3_4_a_source_registry_is_sanitized_and_policy_rich() -> None:
    """Sources must expose env var names and policies, not secret values."""
    response = client.get("/api/v3/external-ingestion/sources")
    assert response.status_code == 200
    payload = response.json()["data"]

    source_keys = {item["source_key"] for item in payload["sources"]}
    assert {"spotify_web_api", "lastfm_api", "musicbrainz_api", "youtube_data_api", "soundcloud_public_api", "manual_csv_review"}.issubset(source_keys)

    spotify = next(item for item in payload["sources"] if item["source_key"] == "spotify_web_api")
    assert spotify["requires_credentials"] is True
    assert spotify["credential_env_vars"] == ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]
    assert spotify["cache_policy"]["enabled"] is True
    assert spotify["rate_limit_policy"]

    # Credential variable names are intentionally exposed so the developer knows
    # what to configure in backend/.env. The security rule is that real secret
    # values must never be exposed. Strip allowed env-var names before checking
    # for accidental raw secret markers in the serialized payload.
    sanitized_payload = str(payload).lower()
    for source in payload["sources"]:
        assert set(source["credential_status"].values()).issubset({"configured", "missing"})
        for env_var in source["credential_env_vars"]:
            assert env_var == env_var.upper()
            sanitized_payload = sanitized_payload.replace(env_var.lower(), "")

    assert "client_secret" not in sanitized_payload
    assert "access_token" not in sanitized_payload
    assert "password" not in sanitized_payload


def test_v3_4_a_tool_registry_includes_open_source_evaluations() -> None:
    """yt-dlp and NewPipeExtractor must be represented before any integration."""
    response = client.get("/api/v3/external-ingestion/tools")
    assert response.status_code == 200
    tools = response.json()["data"]["tools"]
    by_key = {tool["tool_key"]: tool for tool in tools}

    assert "yt_dlp_metadata_only" in by_key
    assert by_key["yt_dlp_metadata_only"]["decision"] == "evaluate_in_v3_4_c_metadata_only_no_downloads"
    assert by_key["yt_dlp_metadata_only"]["evaluation_payload"]["no_audio_video_download"] is True
    assert by_key["newpipe_extractor_spike"]["decision"] == "evaluated_not_integrated_in_v3_4_a"
    assert by_key["playwright_last_resort"]["decision"] == "last_resort_not_integrated_by_default"


def test_v3_4_a_dry_run_does_not_create_external_data() -> None:
    """Dry-run may inspect scope but must not persist snapshots or metrics."""
    with SessionLocal() as db:
        snapshots_before = int(db.scalar(select(func.count()).select_from(RawSnapshotModel)) or 0)
        metrics_before = int(db.scalar(select(func.count()).select_from(NormalizedMetricModel)) or 0)

    response = client.post("/api/v3/external-ingestion/dry-run", json={"limit": 5, "sources": ["spotify_web_api", "youtube_data_api"]})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dry_run"] is True
    assert data["would_persist_raw_snapshots"] is False
    assert data["would_persist_normalized_metrics"] is False
    assert "spotify_web_api" in data["selected_sources"]

    with SessionLocal() as db:
        snapshots_after = int(db.scalar(select(func.count()).select_from(RawSnapshotModel)) or 0)
        metrics_after = int(db.scalar(select(func.count()).select_from(NormalizedMetricModel)) or 0)

    assert snapshots_after == snapshots_before
    assert metrics_after == metrics_before


def test_v3_4_a_deduplication_helpers_are_stable() -> None:
    """Same normalized payload must produce stable hashes and snapshot keys."""
    payload_a = {"followers": 10, "artist": "Angerfist"}
    payload_b = {"artist": "Angerfist", "followers": 10}

    assert content_hash(payload_a) == content_hash(payload_b)
    key_a = build_snapshot_key(source_key="spotify_web_api", canonical_artist_key="angerfist", collector_key="spotify_official_artist_profile", payload=payload_a)
    key_b = build_snapshot_key(source_key="spotify_web_api", canonical_artist_key="angerfist", collector_key="spotify_official_artist_profile", payload=payload_b)
    assert key_a == key_b


def test_v3_4_a_static_registries_are_not_empty() -> None:
    """Static registries are the source of truth for V3.4-A."""
    assert len(COLLECTOR_REGISTRY) >= 6
    assert len(TOOL_EVALUATION_REGISTRY) >= 8
    assert all(contract.cache_policy.enabled or contract.source_key == "manual_csv_review" for contract in COLLECTOR_REGISTRY)
    assert all(tool.supports_cache or tool.tool_key == "newpipe_extractor_spike" for tool in TOOL_EVALUATION_REGISTRY)
