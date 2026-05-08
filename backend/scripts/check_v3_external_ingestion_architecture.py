"""Validate V3.4-A external collector architecture.

Run from repository root after applying migrations:

    python backend/scripts/check_v3_external_ingestion_architecture.py

The script is deliberately offline: it checks tables, source/tool registries,
secret-safety contracts and dry-run behavior, but never calls external APIs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.collectors.registry import COLLECTOR_REGISTRY, TOOL_EVALUATION_REGISTRY
from app.db.database import engine
from app.main import app

EXPECTED_TABLES = {
    "source_tool_evaluations",
    "collector_runs",
    "collector_run_items",
    "raw_sources",
    "raw_snapshots",
    "normalized_metrics",
}
EXPECTED_COLLECTOR_FILES = {
    "backend/app/collectors/base.py",
    "backend/app/collectors/contracts.py",
    "backend/app/collectors/errors.py",
    "backend/app/collectors/http_client.py",
    "backend/app/collectors/rate_limiter.py",
    "backend/app/collectors/cache.py",
    "backend/app/collectors/normalizers.py",
    "backend/app/collectors/registry.py",
    "backend/app/collectors/security.py",
    "backend/app/collectors/deduplication.py",
}


def ok(message: str) -> None:
    """Print one OK line."""
    print(f"OK  {message}")


def fail(message: str) -> None:
    """Abort with a clear validation error."""
    raise SystemExit(f"FAIL {message}")


def current_branch() -> str:
    """Return current git branch or unknown outside git."""
    try:
        return subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    """Run all V3.4-A validation checks."""
    print("Nexus Predictor V3.4-A external collector architecture validation")
    print("=" * 72)

    branch = current_branch()
    if branch == "refactor/v3-ml-first":
        ok(f"branch: {branch}")
    else:
        print(f"WARN branch is {branch}; expected refactor/v3-ml-first")

    tables = set(inspect(engine).get_table_names())
    missing_tables = EXPECTED_TABLES - tables
    if missing_tables:
        fail(f"missing V3.4-A tables: {sorted(missing_tables)}")
    ok("V3.4-A tables exist")

    raw_snapshot_columns = {column["name"] for column in inspect(engine).get_columns("raw_snapshots")}
    normalized_metric_columns = {column["name"] for column in inspect(engine).get_columns("normalized_metrics")}
    for column in ("canonical_artist_key", "source_reported_at", "collector_version", "normalizer_version"):
        if column not in raw_snapshot_columns:
            fail(f"raw_snapshots missing {column}")
    for column in ("canonical_artist_key", "metric_schema_version", "collector_version", "normalizer_version", "is_diagnostic_only"):
        if column not in normalized_metric_columns:
            fail(f"normalized_metrics missing {column}")
    ok("raw snapshot and normalized metric lineage columns exist")

    for path in EXPECTED_COLLECTOR_FILES:
        if not (REPO_ROOT / path).exists():
            fail(f"missing collector file: {path}")
    ok("collector package structure exists")

    if len(COLLECTOR_REGISTRY) < 6:
        fail("collector registry is too small")
    if len(TOOL_EVALUATION_REGISTRY) < 8:
        fail("tool evaluation registry is too small")
    ok("collector and tool registries are populated")

    client = TestClient(app)
    architecture = client.get("/api/v3/external-ingestion/architecture")
    if architecture.status_code != 200:
        fail(f"architecture endpoint failed: {architecture.status_code}")
    arch_data = architecture.json()["data"]
    if not arch_data["ready"]:
        fail(f"architecture endpoint is not ready: {arch_data['warnings']}")
    ok("architecture endpoint works")

    sources = client.get("/api/v3/external-ingestion/sources")
    if sources.status_code != 200:
        fail(f"sources endpoint failed: {sources.status_code}")
    source_payload = sources.json()["data"]
    if source_payload["total"] < 6:
        fail("sources endpoint returned too few sources")
    if "***" in str(source_payload):
        fail("sources endpoint appears to expose redacted marker as value unexpectedly")
    forbidden_secret_values = ["SPOTIFY_CLIENT_SECRET=", "LASTFM_API_KEY="]
    if any(secret in str(source_payload) for secret in forbidden_secret_values):
        fail("sources endpoint leaked secret-like payload")
    ok("sources endpoint works without leaking credential values")

    tools = client.get("/api/v3/external-ingestion/tools")
    if tools.status_code != 200:
        fail(f"tools endpoint failed: {tools.status_code}")
    tool_payload = tools.json()["data"]
    decisions = {item["tool_key"]: item["decision"] for item in tool_payload["tools"]}
    if decisions.get("newpipe_extractor_spike") != "evaluated_not_integrated_in_v3_4_a":
        fail("NewPipeExtractor must be evaluated but not integrated in V3.4-A")
    if "yt_dlp_metadata_only" not in decisions:
        fail("yt-dlp metadata-only must be present in the tool registry")
    ok("tool evaluation endpoint works")

    dry_run = client.post("/api/v3/external-ingestion/dry-run", json={"limit": 5, "sources": ["spotify_web_api", "youtube_data_api"]})
    if dry_run.status_code != 200:
        fail(f"dry-run endpoint failed: {dry_run.status_code}")
    dry_data = dry_run.json()["data"]
    if dry_data["would_persist_raw_snapshots"] or dry_data["would_persist_normalized_metrics"]:
        fail("dry-run must not persist raw snapshots or normalized metrics")
    ok("dry-run endpoint is offline and non-persistent")

    print("=" * 72)
    print("V3.4-A external collector architecture is ready.")


if __name__ == "__main__":
    main()
