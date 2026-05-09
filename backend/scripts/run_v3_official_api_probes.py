"""Run V3.4-B official API probes from the console.

This script may make real external calls only when --execute-real-calls is set.
It persists raw snapshots and normalized metric candidates only when --persist is
also provided.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.schemas.external_ingestion_v3 import V34OfficialProbeRequest  # noqa: E402
from app.services.v3_external_api_probe_service import V3ExternalAPIProbeService  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run V3.4-B official API probes.")
    parser.add_argument("--limit", type=int, default=5, help="Number of Nexus 2026 artists to probe.")
    parser.add_argument(
        "--sources",
        default="spotify_web_api,lastfm_api,musicbrainz_api",
        help="Comma-separated source keys. Defaults to configured official APIs expected in V3.4-B.",
    )
    parser.add_argument("--execute-real-calls", action="store_true", help="Actually call external APIs.")
    parser.add_argument("--persist", action="store_true", help="Persist raw snapshots and normalized metrics.")
    return parser.parse_args()


def main() -> int:
    """Run probes and print a concise status table."""
    args = parse_args()
    sources = [source.strip() for source in args.sources.split(",") if source.strip()]
    request = V34OfficialProbeRequest(
        limit=args.limit,
        sources=sources,
        execute_real_calls=args.execute_real_calls,
        persist=args.persist,
        started_by="run_v3_official_api_probes.py",
    )
    with SessionLocal() as db:
        response = V3ExternalAPIProbeService(db).run_official_probes(request)

    print("Nexus Predictor V3.4-B official API probes")
    print("=" * 72)
    print(f"selected_artist_count: {response.selected_artist_count}")
    print(f"selected_sources: {', '.join(response.selected_sources)}")
    print(f"execute_real_calls: {response.execute_real_calls}")
    print(f"persist: {response.persist}")
    print(f"collector_run_id: {response.collector_run_id}")
    print(f"raw_snapshots_created: {response.raw_snapshots_created}")
    print(f"normalized_metrics_created: {response.normalized_metrics_created}")
    if response.warnings:
        print("warnings:")
        for warning in response.warnings:
            print(f"  - {warning}")
    print("results:")
    for item in response.results:
        print(f"  - {item.canonical_artist_key} | {item.source_key} | {item.status} | metrics={item.metric_count}")
    print("=" * 72)
    print("V3.4-B official API probe run completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
