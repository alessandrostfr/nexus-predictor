"""Run the V2.3 external ingestion Prefect flow.

Run from backend/:

    python scripts/run_external_ingestion.py --reset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# When this script is executed as "python scripts/run_external_ingestion.py",
# Python places backend/scripts in sys.path. Add backend so "app" imports work.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipelines.flows.external_ingestion_flow import external_ingestion_flow  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Nexus Predictor V2.3 external ingestion.")
    parser.add_argument("--reset", action="store_true", help="Rebuild only V2.3 rows.")
    parser.add_argument("--limit-artists", type=int, default=None, help="Process only the first N unique artists.")
    parser.add_argument("--probe-sources", action="store_true", help="Run non-blocking HTTP source probes.")
    return parser.parse_args()


def main() -> None:
    """Run the Prefect flow and print its summary."""
    args = parse_args()
    result = external_ingestion_flow(
        reset=args.reset,
        limit_artists=args.limit_artists,
        probe_sources=args.probe_sources,
    )
    print(result)


if __name__ == "__main__":
    main()
