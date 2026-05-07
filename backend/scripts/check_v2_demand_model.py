"""Validate Nexus Predictor V2.7 demand model.

Usage from backend/:
    python scripts/check_v2_demand_model.py
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.demand_model_service import MODEL_VERSION, DemandModelService  # noqa: E402


def main() -> None:
    """Rebuild the V2.7 model and assert its core contracts."""
    with SessionLocal() as db:
        service = DemandModelService(db)
        result = service.rebuild(2026, reset=True)
        coverage = service.coverage(2026)
        ranking = service.list_predictions(2026, limit=20)
        project_one = service.get_prediction(2026, "project-one")
        comparison = service.compare_v1_v2(2026, limit=50)

    if coverage is None or ranking is None or project_one is None or comparison is None:
        raise RuntimeError("V2.7 demand-model validation could not load required payloads.")
    if result.model_version != MODEL_VERSION:
        raise RuntimeError("Unexpected model version.")
    if result.predictions <= 0:
        raise RuntimeError("No V2.7 predictions were generated.")
    if coverage.persisted_predictions != result.predictions:
        raise RuntimeError("Coverage count does not match rebuild result.")
    if coverage.total_artists <= 0:
        raise RuntimeError("No artists were found for 2026.")
    if coverage.fallback_predictions >= coverage.persisted_predictions:
        raise RuntimeError("Every prediction used fallback mode; external feature coverage is not being used.")
    if len(ranking.items) < 10:
        raise RuntimeError("The V2.7 ranking should return at least ten artists.")
    if ranking.items[0].demand_score < ranking.items[-1].demand_score:
        raise RuntimeError("The V2.7 ranking is not sorted by demand score.")
    if project_one.demand_score < 55:
        raise RuntimeError("Project One should retain strong demand context in V2.7.")
    if not project_one.features or not project_one.factors or not project_one.explanations:
        raise RuntimeError("V2.7 artist predictions must include features, factors and explanations.")
    if comparison.total <= 0 or not comparison.items:
        raise RuntimeError("V1/V2 comparison did not return rows.")

    print("Nexus Predictor V2.7 demand-model check")
    print(f"Rebuild result: {result.model_dump(mode='json')}")
    print(f"Coverage: {coverage.model_dump(mode='json')}")
    print(f"Top artist: {ranking.items[0].artist_slug} -> {ranking.items[0].demand_score}")
    print("V2.7 demand-model check completed successfully.")


if __name__ == "__main__":
    main()
