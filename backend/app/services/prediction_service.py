"""Prediction service for attendance and artist demand.

The service combines researched Nexus history, the Block 4 genre classifier and
editable manual weights. It does not train a heavy ML model yet because we do not
have reliable labelled per-room attendance data. Instead it returns transparent
scores that can later become features for scikit-learn.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.paths import PREDICTIONS_DIR
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.genre import ClassifiedArtistGenre
from app.schemas.prediction import (
    ArtistDemandPrediction,
    ArtistDemandPredictionList,
    AttendancePrediction,
    EditionPrediction,
    PredictionFactor,
)
from app.services.genre_classifier import GenreClassifierService
from app.services.scoring_service import (
    GENRE_STRENGTH_WEIGHTS,
    MANUAL_HYPE_WEIGHTS,
    SPECIAL_PERFORMANCE_BONUS,
    attendance_confidence,
    confidence_from_score,
    factor,
    normalize_score,
    risk_from_score,
)


class PredictionService:
    """Build deterministic predictions for the Nexus Predictor MVP."""

    def __init__(self, db: Session) -> None:
        """Create repository and classifier dependencies."""
        self.repository = SQLiteRepository(db)
        self.genre_classifier = GenreClassifierService(db)

    def get_edition_prediction(self, year: int = 2026, *, artist_limit: int = 20) -> EditionPrediction | None:
        """Return the full prediction payload for a Nexus edition."""
        edition = self.repository.get_edition(year)
        if edition is None:
            return None

        artist_predictions = self._ranked_artist_predictions(year)
        attendance = self.predict_attendance(year, artist_predictions=artist_predictions)
        genre_distribution = self._genre_distribution(year)

        return EditionPrediction(
            year=year,
            edition_name=str(edition.get("name") or f"Nexus Festival {year}"),
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_status="interpretable_scoring_v1",
            attendance=attendance,
            top_artist_predictions=artist_predictions[:artist_limit],
            genre_distribution=genre_distribution,
            total_artist_predictions=len(artist_predictions),
        )

    def list_artist_predictions(
        self,
        year: int = 2026,
        *,
        genre: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ArtistDemandPredictionList | None:
        """Return paginated artist demand predictions."""
        if self.repository.get_edition(year) is None:
            return None

        ranked = self._ranked_artist_predictions(year)
        normalized_query = query.lower().strip() if query else None
        filtered: list[ArtistDemandPrediction] = []

        for prediction in ranked:
            if genre and prediction.main_genre.lower() != genre.lower():
                continue
            if normalized_query and normalized_query not in prediction.name.lower():
                continue
            filtered.append(prediction)

        return ArtistDemandPredictionList(
            year=year,
            total=len(filtered),
            limit=limit,
            offset=offset,
            items=filtered[offset : offset + limit],
        )

    def get_artist_prediction(self, year: int, slug: str) -> ArtistDemandPrediction | None:
        """Return one artist demand prediction by slug."""
        ranked = self._ranked_artist_predictions(year)
        for prediction in ranked:
            if prediction.slug == slug:
                return prediction
        return None

    def write_prediction_snapshot(self, year: int = 2026) -> dict[str, Any] | None:
        """Write a JSON prediction snapshot into backend/app/data/predictions."""
        prediction = self.get_edition_prediction(year, artist_limit=1000)
        if prediction is None:
            return None

        PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = PREDICTIONS_DIR / f"{year}_prediction.json"
        payload = prediction.model_dump(mode="json")
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"year": year, "path": str(output_path), "artists": prediction.total_artist_predictions}

    def predict_attendance(
        self,
        year: int = 2026,
        *,
        artist_predictions: list[ArtistDemandPrediction] | None = None,
    ) -> AttendancePrediction:
        """Predict edition attendance using historical ranges and 2026 lineup strength."""
        editions = [edition for edition in self.repository.list_editions() if edition["year"] < year]
        detailed_editions = [self.repository.get_edition(edition["year"]) for edition in editions]
        valid_editions = [edition for edition in detailed_editions if edition is not None]

        historical_midpoints = [
            int(edition.get("attendance", {}).get("estimated_mid") or 0)
            for edition in valid_editions
            if int(edition.get("attendance", {}).get("estimated_mid") or 0) > 0
        ]
        baseline = historical_midpoints[-1] if historical_midpoints else 7000
        current = self.repository.get_edition(year) or {}
        current_artists = int(current.get("artist_count") or 0)
        current_duration = int(current.get("duration_hours") or 0)
        current_stages = int(current.get("stage_count") or 0)

        artist_predictions = artist_predictions or self._ranked_artist_predictions(year)
        top_scores = [artist.demand_score for artist in artist_predictions[:12]]
        avg_top_score = sum(top_scores) / len(top_scores) if top_scores else 50.0
        returning_share = self._returning_artist_share(year)

        # Multipliers are intentionally conservative because historical
        # attendance values are seed ranges, not confirmed ticket scans.
        lineup_multiplier = 1.0 + min(max((current_artists - 60) / 180, 0.0), 0.22)
        duration_multiplier = 1.0 + min(max((current_duration - 12) / 100, 0.0), 0.14)
        stage_multiplier = 1.0 + min(max((current_stages - 6) / 40, 0.0), 0.12)
        demand_multiplier = 1.0 + min(max((avg_top_score - 55) / 220, 0.0), 0.18)
        returning_multiplier = 1.0 + min(returning_share * 0.12, 0.12)

        predicted_mid = int(
            baseline
            * lineup_multiplier
            * duration_multiplier
            * stage_multiplier
            * demand_multiplier
            * returning_multiplier
        )
        predicted_low = int(predicted_mid * 0.84)
        predicted_high = int(predicted_mid * 1.18)

        factors = [
            factor(
                "historical_baseline",
                "Historical baseline",
                float(baseline),
                float(max(historical_midpoints) if historical_midpoints else baseline),
                "Uses the latest historical attendance seed as the baseline because exact public attendance is not confirmed.",
            ),
            factor(
                "lineup_size",
                "Lineup size",
                round((lineup_multiplier - 1.0) * 100, 2),
                22.0,
                f"Current lineup has {current_artists} artists, increasing expected draw compared with smaller editions.",
            ),
            factor(
                "event_duration",
                "Event duration",
                round((duration_multiplier - 1.0) * 100, 2),
                14.0,
                f"Current duration seed is {current_duration} hours.",
            ),
            factor(
                "stage_count",
                "Stage count",
                round((stage_multiplier - 1.0) * 100, 2),
                12.0,
                f"Current stage count seed is {current_stages}.",
            ),
            factor(
                "top_artist_demand",
                "Top artist demand",
                round((demand_multiplier - 1.0) * 100, 2),
                18.0,
                f"Average demand score of the top 12 predicted artists is {avg_top_score:.1f}.",
            ),
            factor(
                "returning_artists",
                "Returning artists",
                round((returning_multiplier - 1.0) * 100, 2),
                12.0,
                f"{returning_share:.0%} of the current lineup has previous Nexus history in the dataset.",
            ),
        ]

        return AttendancePrediction(
            year=year,
            predicted_low=predicted_low,
            predicted_mid=predicted_mid,
            predicted_high=predicted_high,
            confidence=attendance_confidence(len(historical_midpoints), bool(current_artists)),
            method="interpretable_historical_growth_model_v1",
            baseline_years=[int(edition["year"]) for edition in editions],
            factors=factors,
            notes=[
                "Attendance is a prediction range, not an official figure.",
                "Historical attendance inputs remain low-confidence seeds until official attendance by edition is found.",
                "The model will become stronger when timetable, stage assignment and ticketing signals are available.",
            ],
        )

    def _ranked_artist_predictions(self, year: int) -> list[ArtistDemandPrediction]:
        """Build, sort and rank all artist predictions for an edition."""
        artists = self.repository.list_artists(year=year, limit=10000)["items"]
        predictions = [self._score_artist(year, artist) for artist in artists]
        predictions.sort(key=lambda item: (-item.demand_score, item.name.lower()))

        ranked: list[ArtistDemandPrediction] = []
        for index, prediction in enumerate(predictions, start=1):
            ranked.append(prediction.model_copy(update={"rank": index}))
        return ranked

    def _score_artist(self, year: int, artist: dict[str, Any]) -> ArtistDemandPrediction:
        """Score one artist with explicit factor explanations."""
        slug = str(artist.get("slug") or "")
        name = str(artist.get("name") or slug)
        classification = self.genre_classifier.get_artist_classification(slug) or self._fallback_classification(artist)
        appearance_years = sorted(int(item) for item in artist.get("appearance_years", []) if int(item) <= year)
        previous_years = [item for item in appearance_years if item < year]
        current_performances = [
            appearance
            for appearance in artist.get("appearances", [])
            if int(appearance.get("year") or 0) == year
        ]
        performance_names = [str(item.get("performance_display_name") or name) for item in current_performances]
        performance_types = sorted({str(item.get("performance_type") or "solo") for item in current_performances}) or ["solo"]

        base_contribution = 18.0
        history_contribution = min(len(previous_years) * 6.0, 24.0)
        returning_contribution = 10.0 if previous_years else 0.0
        recent_contribution = 8.0 if any(previous >= year - 2 for previous in previous_years) else 0.0
        genre_contribution = GENRE_STRENGTH_WEIGHTS.get(classification.main_genre, 5.0)
        manual_hype = MANUAL_HYPE_WEIGHTS.get(slug, 0.0)
        performance_bonus = max(SPECIAL_PERFORMANCE_BONUS.get(kind, 0.0) for kind in performance_types)
        special_show_bonus = 5.0 if classification.is_special_show else 0.0
        unknown_penalty = -6.0 if classification.main_genre == "Unknown" else 0.0
        review_penalty = -3.0 if classification.needs_manual_review and classification.main_genre == "Unknown" else 0.0

        factors: list[PredictionFactor] = [
            factor(
                "base_lineup_presence",
                "Lineup presence",
                base_contribution,
                18.0,
                "Every confirmed 2026 lineup artist starts with a base score.",
            ),
            factor(
                "historical_appearances",
                "Historical Nexus appearances",
                history_contribution,
                24.0,
                f"Previous Nexus years in dataset: {previous_years or 'none'}.",
            ),
            factor(
                "returning_artist",
                "Returning artist bonus",
                returning_contribution,
                10.0,
                "Returning artists are more likely to have an established Nexus audience.",
            ),
            factor(
                "recent_presence",
                "Recent presence",
                recent_contribution,
                8.0,
                "Adds weight if the artist appeared in the last two researched editions.",
            ),
            factor(
                "genre_strength",
                "Subgenre demand context",
                genre_contribution,
                max(GENRE_STRENGTH_WEIGHTS.values()),
                f"Classified as {classification.main_genre} by the Block 4 genre system.",
            ),
            factor(
                "manual_hype_signal",
                "Manual hype signal",
                manual_hype,
                max(MANUAL_HYPE_WEIGHTS.values()),
                "Editable MVP hype signal for iconic projects, headliners and very high-interest acts.",
            ),
            factor(
                "performance_format",
                "Performance format",
                performance_bonus,
                max(SPECIAL_PERFORMANCE_BONUS.values()),
                f"Current performance type(s): {', '.join(performance_types)}.",
            ),
            factor(
                "special_show",
                "Special show handling",
                special_show_bonus,
                5.0,
                "Special shows and label concepts can concentrate demand beyond a normal solo set.",
            ),
        ]

        if unknown_penalty:
            factors.append(
                factor(
                    "unknown_genre_penalty",
                    "Unknown genre penalty",
                    unknown_penalty,
                    0.0,
                    "Artist still needs reliable subgenre classification, so confidence is reduced.",
                )
            )
        if review_penalty:
            factors.append(
                factor(
                    "manual_review_penalty",
                    "Manual review penalty",
                    review_penalty,
                    0.0,
                    "Unknown artists marked for review are scored conservatively until curated.",
                )
            )

        raw_score = sum(item.contribution for item in factors)
        demand_score = normalize_score(raw_score)
        notes = []
        if classification.is_special_show:
            notes.append("Special show/project: keep separated from canonical artist matching.")
        if classification.main_genre == "Unknown":
            notes.append("Needs manual genre review before the prediction should be considered stable.")

        return ArtistDemandPrediction(
            year=year,
            slug=slug,
            name=name,
            main_genre=classification.main_genre,
            artist_kind=classification.artist_kind,
            is_special_show=classification.is_special_show,
            demand_score=demand_score,
            crowd_risk=risk_from_score(demand_score),
            confidence=confidence_from_score(
                demand_score,
                unknown_genre=classification.main_genre == "Unknown",
                prior_years=len(previous_years),
            ),
            performance_names=performance_names,
            performance_types=performance_types,
            appearance_count=int(artist.get("appearance_count") or 0),
            previous_appearance_years=previous_years,
            factors=factors,
            notes=notes,
        )

    def _returning_artist_share(self, year: int) -> float:
        """Return the share of current artists that appeared before target year."""
        artists = self.repository.list_artists(year=year, limit=10000)["items"]
        if not artists:
            return 0.0
        returning = 0
        for artist in artists:
            previous_years = [int(item) for item in artist.get("appearance_years", []) if int(item) < year]
            if previous_years:
                returning += 1
        return returning / len(artists)

    def _genre_distribution(self, year: int) -> list[dict[str, Any]]:
        """Return a compact, prediction-safe genre distribution.

        Block 4 genre distribution items may include taxonomy metadata such as
        aliases, parent groups or raw rule data. That is useful for genre
        endpoints, but the prediction snapshot only needs stable numeric fields.
        Compacting the payload prevents Pydantic validation errors when the
        taxonomy contains lists or null values.
        """
        distribution = self.genre_classifier.get_edition_genre_distribution(year)
        if distribution is None:
            return []

        compact_distribution: list[dict[str, Any]] = []
        for item in distribution.distribution:
            payload = item.model_dump(mode="json")
            artist_count = int(payload.get("artist_count") or 0)
            total_artists = int(getattr(distribution, "total_artists", 0) or 0)
            percentage = round((artist_count / total_artists) * 100, 2) if total_artists else None

            compact_distribution.append(
                {
                    "name": str(payload.get("name") or "Unknown"),
                    "artist_count": artist_count,
                    "percentage": percentage,
                    "raw": payload,
                }
            )

        return compact_distribution

    def _fallback_classification(self, artist: dict[str, Any]) -> ClassifiedArtistGenre:
        """Build a minimal fallback if a classification is unexpectedly missing."""
        return ClassifiedArtistGenre(
            slug=str(artist.get("slug") or ""),
            name=str(artist.get("name") or ""),
            normalized_name=str(artist.get("normalized_name") or artist.get("name") or ""),
            main_genre=str(artist.get("primary_genre_seed") or "Unknown"),
            primary_genre_seed=str(artist.get("primary_genre_seed") or "Unknown"),
            genre_source="fallback_seed",
            confidence="low",
            appearance_count=int(artist.get("appearance_count") or 0),
            appearance_years=list(artist.get("appearance_years") or []),
        )
