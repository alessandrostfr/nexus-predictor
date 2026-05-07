"""Prefect flow for V2.3 external ingestion.

Run from backend/:

    python -m app.pipelines.flows.external_ingestion_flow --reset
"""

from __future__ import annotations

import argparse
from typing import Any

from prefect import flow

from app.pipelines.tasks.external_ingestion_tasks import (
    get_external_ingestion_coverage,
    load_external_ingestion_seed,
    probe_source_url,
    run_external_ingestion_service,
)


@flow(name="nexus-v2-external-ingestion", log_prints=True)
def external_ingestion_flow(
    *,
    reset: bool = False,
    limit_artists: int | None = None,
    probe_sources: bool = False,
) -> dict[str, Any]:
    """Run the V2.3 external ingestion flow.

    Args:
        reset: Rebuild only V2.3 external-ingestion rows.
        limit_artists: Optional number of unique artists to process from the seed.
        probe_sources: Optional best-effort source URL checks. Failures are warnings.

    Returns:
        A dictionary with run summary, coverage and non-blocking warnings.
    """
    seed = load_external_ingestion_seed()
    probes: list[dict[str, Any]] = []

    if probe_sources:
        for source in seed.get("sources", []):
            probes.append(probe_source_url(source["key"], source.get("base_url")))

    summary = run_external_ingestion_service(reset=reset, limit_artists=limit_artists)
    coverage = get_external_ingestion_coverage()

    warnings = list(summary.get("warnings", []))
    warnings.extend(
        f"{probe['source_key']} probe failed: {probe.get('error') or probe.get('status_code')}"
        for probe in probes
        if not probe.get("ok")
    )
    summary["warnings"] = warnings

    return {
        "summary": summary,
        "coverage": coverage,
        "source_probes": probes,
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for direct flow execution."""
    parser = argparse.ArgumentParser(description="Run Nexus Predictor V2.3 external ingestion.")
    parser.add_argument("--reset", action="store_true", help="Rebuild only V2.3 external-ingestion rows.")
    parser.add_argument("--limit-artists", type=int, default=None, help="Process only the first N unique artists.")
    parser.add_argument(
        "--probe-sources",
        action="store_true",
        help="Run non-blocking HTTP checks against configured source base URLs.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    result = external_ingestion_flow(
        reset=args.reset,
        limit_artists=args.limit_artists,
        probe_sources=args.probe_sources,
    )
    print(result)


if __name__ == "__main__":
    main()
