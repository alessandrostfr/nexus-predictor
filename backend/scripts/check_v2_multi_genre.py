"""Validate Nexus Predictor V2.5 multi-genre classification.

Run from backend/ with the virtual environment active:

    python scripts/check_v2_multi_genre.py
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.multi_genre_service import MultiGenreClassifierService  # noqa: E402


def main() -> None:
    """Run a concrete V2.5 validation against the local database."""
    with SessionLocal() as db:
        service = MultiGenreClassifierService(db)
        result = service.rebuild(reset=True)
        coverage = result.coverage

        print("Nexus Predictor V2.5 multi-genre check")
        print(f"Rebuild result: {result.model_dump()}")

        assert result.artists_processed >= 100, "Expected the historical artist index to be loaded."
        assert result.genre_rows >= result.artists_processed, "Every artist should have at least one genre row."
        assert result.evidence_items >= result.artists_processed, "Every artist should receive genre evidence."
        assert coverage.classified_ratio >= 0.75, "V2.5 should strongly reduce Unknown classifications."
        assert coverage.artists_with_secondary_genres > 0, "Secondary genre chips should be generated."

        project_one = service.get_artist_classification("project-one")
        assert project_one is not None, "Project One should exist."
        assert project_one.main_genre == "Classic / Legacy Hardstyle"
        assert "Hardstyle" in project_one.secondary_genres
        assert project_one.genre_sources, "Project One should expose genre sources."

        angerfist = service.get_artist_classification("angerfist")
        assert angerfist is not None and angerfist.main_genre == "Hardcore"
        assert angerfist.genre_confidence in {"high", "verified"}

        dual_damage = service.get_artist_classification("dual-damage")
        assert dual_damage is not None and dual_damage.main_genre == "Xtra Raw"
        assert "Rawstyle" in dual_damage.secondary_genres

        comparison = service.compare_v1_v2(limit=1000)
        assert comparison.unknown_reduced > 0, "V2.5 should classify artists that were Unknown in V1."

        print("V2.5 multi-genre check completed successfully.")


if __name__ == "__main__":
    main()
