"""Prefect flow for Nexus Predictor V2.4 social/platform ingestion."""

from __future__ import annotations

import argparse

from prefect import flow

from app.pipelines.tasks.social_platform_tasks import (
    load_social_platform_inputs,
    run_social_platform_service,
    social_platform_coverage,
)


@flow(name="nexus-v2-social-platform-ingestion")
def social_platform_ingestion_flow(reset: bool = False, limit_artists: int | None = None) -> dict[str, object]:
    """Run the V2.4 mixed social/platform ingestion pipeline."""
    inputs = load_social_platform_inputs()
    summary = run_social_platform_service(reset=reset, limit_artists=limit_artists)
    coverage = social_platform_coverage()
    return {
        "inputs": inputs,
        "summary": summary,
        "coverage": coverage,
    }


def main() -> None:
    """CLI entrypoint used by local validations."""
    parser = argparse.ArgumentParser(description="Run V2.4 social/platform ingestion flow.")
    parser.add_argument("--reset", action="store_true", help="Rebuild only V2.4 social/platform rows.")
    parser.add_argument("--limit-artists", type=int, default=None, help="Optional artist limit for quick tests.")
    args = parser.parse_args()

    result = social_platform_ingestion_flow(reset=args.reset, limit_artists=args.limit_artists)
    print(result)


if __name__ == "__main__":
    main()
