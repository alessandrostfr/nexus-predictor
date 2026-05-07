"""V2.7 demand and popularity model.

The V2.7 model replaces the MVP-only scoring logic with an evidence-backed
feature model. It is still intentionally interpretable because Nexus does not
yet have enough labelled crowd-density observations to justify a black-box
supervised model. The service uses the PostgreSQL evidence layer, Spotify
cache, social/platform metrics, career signals, multi-genre rows and
historical timetable slots to produce separated score components.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ArtistGenreModel,
    ArtistMetricModel,
    ArtistModel,
    CareerEventModel,
    EvidenceItemModel,
    HistoricalTimetableSlotModel,
    SpotifyArtistCacheModel,
    V2ArtistDemandPredictionModel,
)
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.prediction import (
    PredictionFactor,
    V2DemandFeature,
    V2DemandModelCoverage,
    V2DemandPrediction,
    V2DemandPredictionList,
    V2DemandRebuildResult,
    V2ModelComparisonItem,
    V2ModelComparisonResponse,
)
from app.services.prediction_service import PredictionService
from app.services.scoring_service import MANUAL_HYPE_WEIGHTS, factor, normalize_score, risk_from_score

MODEL_VERSION = "v2.7-interpretable-feature-model"
MODEL_METHOD = "evidence_weighted_interpretable_model"

# V2.7 deliberately keeps weights explicit. They are part of the model
# explanation and can be tuned later when real validation data appears.
SCORE_WEIGHTS = {
    "popularity_score": 0.30,
    "career_score": 0.25,
    "momentum_score": 0.20,
    "nexus_affinity_score": 0.25,
}

GENRE_DEMAND_MODIFIERS: dict[str, float] = {
    "Classic / Legacy Hardstyle": 5.0,
    "Rawstyle": 4.0,
    "Xtra Raw": 4.0,
    "Uptempo Hardcore": 3.5,
    "Hardcore": 3.0,
    "Frenchcore": 3.0,
    "Industrial Hardcore": 2.0,
    "Euphoric Hardstyle": 2.0,
    "Mainstage Hard Dance": 2.0,
    "Happy Hardcore": 1.0,
    "Freestyle / Hard Dance": 0.5,
    "Unknown": -4.0,
}


@dataclass(frozen=True)
class MetricSnapshot:
    """Compact lookup container for numeric metrics and evidence counts."""

    numeric: dict[str, float]
    evidence_count: int


class DemandModelService:
    """Generate, persist and expose V2.7 artist demand predictions."""

    def __init__(self, db: Session) -> None:
        """Store the request-scoped session and compatible V1 repository."""
        self.db = db
        self.repository = SQLiteRepository(db)
        self.v1_service = PredictionService(db)

    def rebuild(self, year: int = 2026, *, reset: bool = True) -> V2DemandRebuildResult:
        """Rebuild persisted V2.7 predictions for one edition year."""
        if self.repository.get_edition(year) is None:
            raise ValueError(f"Edition {year} was not found.")

        if reset:
            self.db.execute(delete(V2ArtistDemandPredictionModel).where(V2ArtistDemandPredictionModel.year == year))
            self.db.commit()

        artists = self.repository.list_artists(year=year, limit=10000)["items"]
        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        predictions = [self._score_artist(year, artist, generated_at=generated_at) for artist in artists]
        predictions.sort(key=lambda item: (-item.demand_score, item.artist_name.lower()))

        fallback_predictions = 0
        for rank, prediction in enumerate(predictions, start=1):
            prediction.rank = rank
            if prediction.fallback_used:
                fallback_predictions += 1

            # SQLAlchemy merge only knows primary keys, not unique constraints.
            # When reset=false, preserve the existing row id so the rebuild
            # remains idempotent instead of violating uq_v2_artist_demand_year_artist.
            existing = self.db.scalar(
                select(V2ArtistDemandPredictionModel).where(
                    V2ArtistDemandPredictionModel.year == year,
                    V2ArtistDemandPredictionModel.artist_slug == prediction.artist_slug,
                )
            )
            if existing is not None:
                prediction.id = existing.id
                prediction.created_at = existing.created_at
            self.db.merge(prediction)

        self.db.commit()

        top = predictions[0] if predictions else None
        return V2DemandRebuildResult(
            year=year,
            model_version=MODEL_VERSION,
            predictions=len(predictions),
            fallback_predictions=fallback_predictions,
            top_artist_slug=top.artist_slug if top else None,
            top_artist_score=round(top.demand_score, 2) if top else None,
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat(),
        )

    def list_predictions(
        self,
        year: int = 2026,
        *,
        genre: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> V2DemandPredictionList | None:
        """Return persisted V2.7 predictions, rebuilding lazily when empty."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_predictions(year)

        statement = select(V2ArtistDemandPredictionModel).where(V2ArtistDemandPredictionModel.year == year)
        if genre:
            statement = statement.where(func.lower(V2ArtistDemandPredictionModel.main_genre) == genre.lower())
        if query:
            needle = f"%{query.lower().strip()}%"
            statement = statement.where(
                func.lower(V2ArtistDemandPredictionModel.artist_name).like(needle)
                | func.lower(V2ArtistDemandPredictionModel.artist_slug).like(needle)
            )
        statement = statement.order_by(V2ArtistDemandPredictionModel.rank.asc().nullslast(), V2ArtistDemandPredictionModel.demand_score.desc())

        rows = list(self.db.scalars(statement).all())
        return V2DemandPredictionList(
            year=year,
            total=len(rows),
            limit=limit,
            offset=offset,
            items=[self._row_to_schema(row) for row in rows[offset : offset + limit]],
        )

    def get_prediction(self, year: int, artist_slug: str) -> V2DemandPrediction | None:
        """Return one V2.7 artist prediction."""
        self._ensure_predictions(year)
        row = self.db.scalar(
            select(V2ArtistDemandPredictionModel).where(
                V2ArtistDemandPredictionModel.year == year,
                V2ArtistDemandPredictionModel.artist_slug == artist_slug,
            )
        )
        return self._row_to_schema(row) if row else None

    def coverage(self, year: int = 2026) -> V2DemandModelCoverage | None:
        """Return model coverage and quality counters."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_predictions(year)

        artists = self.repository.list_artists(year=year, limit=10000)["items"]
        artist_slugs = {str(artist.get("slug")) for artist in artists}
        rows = list(
            self.db.scalars(
                select(V2ArtistDemandPredictionModel).where(V2ArtistDemandPredictionModel.year == year)
            ).all()
        )
        metrics_by_artist = self._metrics_by_artist(artist_slugs)
        spotify_slugs = {
            row.artist_slug
            for row in self.db.scalars(
                select(SpotifyArtistCacheModel).where(SpotifyArtistCacheModel.artist_slug.in_(artist_slugs))
            ).all()
        }
        external_metric_slugs = {
            slug
            for slug, snapshot in metrics_by_artist.items()
            if any(key.startswith("external.") for key in snapshot.numeric)
        }
        social_metric_slugs = {
            slug
            for slug, snapshot in metrics_by_artist.items()
            if any(key.startswith("social.") or key.startswith("platform.") or key.startswith("lastfm.") for key in snapshot.numeric)
        }
        timetable_slugs = {
            slug
            for slug, snapshot in metrics_by_artist.items()
            if any(key.startswith("historical_timetable.") for key in snapshot.numeric)
        }
        average_score = round(sum(row.demand_score for row in rows) / len(rows), 2) if rows else 0.0
        generated_at = max((row.generated_at for row in rows if row.generated_at), default=None)

        return V2DemandModelCoverage(
            year=year,
            total_artists=len(artists),
            persisted_predictions=len(rows),
            artists_with_external_metrics=len(external_metric_slugs),
            artists_with_spotify=len(spotify_slugs),
            artists_with_social_or_platform_metrics=len(social_metric_slugs),
            artists_with_career_signals=len(external_metric_slugs),
            artists_with_historical_timetable=len(timetable_slugs),
            fallback_predictions=sum(1 for row in rows if row.fallback_used),
            average_demand_score=average_score,
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat() if generated_at else None,
        )

    def compare_v1_v2(self, year: int = 2026, *, limit: int = 100) -> V2ModelComparisonResponse | None:
        """Compare V1 MVP scores with persisted V2.7 scores."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_predictions(year)
        v1_rows = self.v1_service.list_artist_predictions(year=year, limit=10000)
        v1_by_slug = {row.slug: row for row in (v1_rows.items if v1_rows else [])}
        v2_rows = list(
            self.db.scalars(
                select(V2ArtistDemandPredictionModel)
                .where(V2ArtistDemandPredictionModel.year == year)
                .order_by(V2ArtistDemandPredictionModel.rank.asc().nullslast())
            ).all()
        )

        items: list[V2ModelComparisonItem] = []
        for row in v2_rows[:limit]:
            old = v1_by_slug.get(row.artist_slug)
            delta = round(row.demand_score - old.demand_score, 2) if old else None
            items.append(
                V2ModelComparisonItem(
                    artist_slug=row.artist_slug,
                    artist_name=row.artist_name,
                    v1_rank=old.rank if old else None,
                    v1_demand_score=old.demand_score if old else None,
                    v2_rank=row.rank,
                    v2_demand_score=round(row.demand_score, 2),
                    delta=delta,
                    main_reason=self._main_comparison_reason(row, old.demand_score if old else None),
                )
            )

        return V2ModelComparisonResponse(year=year, total=len(v2_rows), limit=limit, items=items)

    def _score_artist(
        self,
        year: int,
        artist_payload: dict[str, Any],
        *,
        generated_at: datetime,
    ) -> V2ArtistDemandPredictionModel:
        """Build one persisted row using normalized evidence-backed features."""
        slug = str(artist_payload.get("slug") or "")
        artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == slug))
        if artist is None:
            raise ValueError(f"Artist {slug} is missing from PostgreSQL seed.")

        metric_snapshot = self._metric_snapshot(slug)
        spotify = self.db.scalar(select(SpotifyArtistCacheModel).where(SpotifyArtistCacheModel.artist_slug == slug))
        primary_genre = self._primary_genre(slug, artist_payload)
        secondary_genres = self._secondary_genres(slug)
        previous_years = [int(item) for item in artist_payload.get("appearance_years", []) if int(item) < year]
        has_current_year = year in [int(item) for item in artist_payload.get("appearance_years", [])]

        features = self._build_features(
            slug=slug,
            artist=artist,
            artist_payload=artist_payload,
            metric_snapshot=metric_snapshot,
            spotify=spotify,
            primary_genre=primary_genre,
            previous_years=previous_years,
            has_current_year=has_current_year,
        )
        feature_map = {item.key: item for item in features}

        popularity_score = self._weighted_average(
            [
                (feature_map["spotify_popularity"].normalized_value, 0.38),
                (feature_map["spotify_followers"].normalized_value, 0.22),
                (feature_map["lastfm_reach"].normalized_value, 0.18),
                (feature_map["social_reach"].normalized_value, 0.14),
                (feature_map["music_platform_presence"].normalized_value, 0.08),
            ]
        )
        career_score = self._weighted_average(
            [
                (feature_map["career_event_count"].normalized_value, 0.22),
                (feature_map["headliner_signals"].normalized_value, 0.28),
                (feature_map["venue_prestige"].normalized_value, 0.24),
                (feature_map["country_reach"].normalized_value, 0.12),
                (feature_map["historical_headliner_slots"].normalized_value, 0.14),
            ]
        )
        momentum_score = self._weighted_average(
            [
                (feature_map["social_momentum"].normalized_value, 0.30),
                (feature_map["engagement"].normalized_value, 0.18),
                (feature_map["lastfm_top_tracks"].normalized_value, 0.18),
                (feature_map["spotify_recent_releases"].normalized_value, 0.14),
                (feature_map["recent_nexus_presence"].normalized_value, 0.20),
            ]
        )
        nexus_affinity_score = self._weighted_average(
            [
                (feature_map["nexus_appearance_count"].normalized_value, 0.32),
                (feature_map["returning_artist"].normalized_value, 0.18),
                (feature_map["historical_timetable_slots"].normalized_value, 0.18),
                (feature_map["current_lineup_presence"].normalized_value, 0.18),
                (feature_map["genre_fit"].normalized_value, 0.14),
            ]
        )

        # Keep a transparent curated prior for iconic 2026 acts. It is capped
        # and separated from the evidence components, so it cannot silently
        # dominate the model and remains reviewable in the factor list.
        curated_prior_modifier = min(MANUAL_HYPE_WEIGHTS.get(slug, 0.0) * 1.1, 35.0)
        raw_demand = (
            popularity_score * SCORE_WEIGHTS["popularity_score"]
            + career_score * SCORE_WEIGHTS["career_score"]
            + momentum_score * SCORE_WEIGHTS["momentum_score"]
            + nexus_affinity_score * SCORE_WEIGHTS["nexus_affinity_score"]
            + GENRE_DEMAND_MODIFIERS.get(primary_genre, 0.0)
            + curated_prior_modifier
        )
        demand_score = normalize_score(raw_demand)
        fallback_used = self._fallback_used(features)
        confidence = self._confidence(features, fallback_used=fallback_used, demand_score=demand_score)
        factors = self._score_factors(
            popularity_score=popularity_score,
            career_score=career_score,
            momentum_score=momentum_score,
            nexus_affinity_score=nexus_affinity_score,
            genre=primary_genre,
            curated_prior_modifier=curated_prior_modifier,
        )
        explanations = self._explanations(slug, features, demand_score=demand_score, fallback_used=fallback_used)
        notes = self._notes(fallback_used=fallback_used, primary_genre=primary_genre, features=features)

        return V2ArtistDemandPredictionModel(
            year=year,
            artist_id=artist.id,
            artist_slug=slug,
            artist_name=artist.name,
            rank=None,
            main_genre=primary_genre,
            secondary_genres_json=json.dumps(secondary_genres, ensure_ascii=False),
            popularity_score=round(popularity_score, 2),
            career_score=round(career_score, 2),
            momentum_score=round(momentum_score, 2),
            nexus_affinity_score=round(nexus_affinity_score, 2),
            demand_score=demand_score,
            crowd_risk=risk_from_score(demand_score),
            confidence=confidence,
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            fallback_used=fallback_used,
            evidence_count=metric_snapshot.evidence_count,
            feature_payload_json=json.dumps([item.model_dump(mode="json") for item in features], ensure_ascii=False),
            factor_payload_json=json.dumps([item.model_dump(mode="json") for item in factors], ensure_ascii=False),
            explanation_json=json.dumps(explanations, ensure_ascii=False),
            notes="\n".join(notes) if notes else None,
            generated_at=generated_at,
        )

    def _build_features(
        self,
        *,
        slug: str,
        artist: ArtistModel,
        artist_payload: dict[str, Any],
        metric_snapshot: MetricSnapshot,
        spotify: SpotifyArtistCacheModel | None,
        primary_genre: str,
        previous_years: list[int],
        has_current_year: bool,
    ) -> list[V2DemandFeature]:
        """Transform raw metrics into normalized features."""
        metric = metric_snapshot.numeric
        appearance_count = float(artist.appearance_count or 0)
        spotify_popularity = float(spotify.popularity or 0) if spotify else self._metric(metric, ["spotify_popularity", "spotify.popularity"])
        spotify_followers = float(spotify.followers or 0) if spotify else self._metric(metric, ["spotify_followers", "spotify.followers_total"])
        spotify_release_count = float(len(self._safe_json(spotify.releases_json, []))) if spotify else self._metric(metric, ["spotify_release_count", "spotify.release_count"])

        lastfm_listeners = self._metric_contains(metric, ["lastfm"], ["listener"])
        lastfm_playcount = self._metric_contains(metric, ["lastfm"], ["playcount", "play_count"])
        lastfm_top_tracks = self._metric(metric, ["lastfm.top_track_count", "lastfm_top_track_count"])
        social_followers = self._metric(metric, ["social.total_followers", "social_total_followers"])
        social_reach = self._metric(metric, ["social.reach_score", "social_reach_score"])
        engagement = self._metric(metric, ["social.engagement_score", "social_engagement_score"])
        social_momentum = self._metric(metric, ["social.momentum_score", "social_momentum_score"])
        platform_presence = self._metric(metric, ["platform.music_presence_score", "platform_music_presence_score"])
        career_event_count = self._metric(metric, ["external.career_event_count"])
        headliner_signal_count = self._metric(metric, ["external.headliner_signal_count"])
        country_count = self._metric(metric, ["external.country_count"])
        venue_prestige = self._metric(metric, ["external.max_venue_prestige_signal"])
        timetable_slots = self._metric(metric, ["historical_timetable.slot_count"])
        timetable_headliners = self._metric(metric, ["historical_timetable.headliner_slot_count"])
        recent_nexus_presence = 100.0 if any(year >= 2024 for year in previous_years) else 0.0
        returning_artist = 100.0 if previous_years else 0.0
        genre_fit = self._genre_fit(primary_genre)

        return [
            self._feature("spotify_popularity", "Spotify popularity", spotify_popularity, spotify_popularity, "spotify.popularity", "high" if spotify else "medium", "Spotify artist popularity from the official API when available."),
            self._feature("spotify_followers", "Spotify followers", spotify_followers, self._log_scale(spotify_followers, 2_500_000), "spotify.followers", "high" if spotify else "medium", "Spotify follower count normalized logarithmically."),
            self._feature("lastfm_reach", "Last.fm reach", max(lastfm_listeners, lastfm_playcount / 8), self._log_scale(max(lastfm_listeners, lastfm_playcount / 8), 300_000), "lastfm.listeners/playcount", "medium", "Last.fm listener/playcount reach signal imported in V2.4."),
            self._feature("social_reach", "Social reach", max(social_reach, self._log_scale(social_followers, 1_000_000)), max(social_reach, self._log_scale(social_followers, 1_000_000)), "social.reach_score", "medium", "Social follower reach from the mixed social/platform ingestion layer."),
            self._feature("music_platform_presence", "Music-platform presence", platform_presence, min(platform_presence, 100), "platform.music_presence_score", "medium", "Presence across Last.fm, SoundCloud, Beatport, YouTube or similar platforms."),
            self._feature("career_event_count", "External career events", career_event_count, min(career_event_count * 18, 100), "external.career_event_count", "low", "Candidate external events from venues, festivals and public listings."),
            self._feature("headliner_signals", "Headliner signals", headliner_signal_count, min(headliner_signal_count * 28, 100), "external.headliner_signal_count", "low", "Candidate headliner or main-stage signals."),
            self._feature("venue_prestige", "Max venue/festival prestige", venue_prestige, min(venue_prestige, 100), "external.max_venue_prestige_signal", "medium", "Maximum prestige score among linked venues or festivals."),
            self._feature("country_reach", "International career reach", country_count, min(country_count * 25, 100), "external.country_count", "low", "Number of countries represented by candidate career signals."),
            self._feature("historical_headliner_slots", "Historical Nexus headliner slots", timetable_headliners, min(timetable_headliners * 34, 100), "historical_timetable.headliner_slot_count", "medium", "Historical Nexus headliner slots from V2.6 timetable dataset."),
            self._feature("social_momentum", "Social momentum", social_momentum, min(social_momentum, 100), "social.momentum_score", "medium", "Recent social/platform activity score from V2.4."),
            self._feature("engagement", "Engagement", engagement, min(engagement, 100), "social.engagement_score", "medium", "Engagement score from social metrics."),
            self._feature("lastfm_top_tracks", "Last.fm top tracks", lastfm_top_tracks, min(lastfm_top_tracks * 10, 100), "lastfm.top_track_count", "high" if lastfm_top_tracks else "medium", "Number of top tracks imported from Last.fm."),
            self._feature("spotify_recent_releases", "Spotify recent releases", spotify_release_count, min(spotify_release_count * 12.5, 100), "spotify.releases", "high" if spotify else "medium", "Recent release count from Spotify cache."),
            self._feature("recent_nexus_presence", "Recent Nexus presence", bool(recent_nexus_presence), recent_nexus_presence, "nexus.appearance_years", "high", "Artist appeared recently in the internal Nexus history."),
            self._feature("nexus_appearance_count", "Nexus appearance count", appearance_count, min(appearance_count * 20, 100), "nexus.appearance_count", "high", "Total Nexus appearances from the internal lineup index."),
            self._feature("returning_artist", "Returning artist", bool(returning_artist), returning_artist, "nexus.appearance_years", "high", "Artist has prior Nexus history before the target edition."),
            self._feature("historical_timetable_slots", "Historical timetable slots", timetable_slots, min(timetable_slots * 18, 100), "historical_timetable.slot_count", "medium", "Number of historical timetable slots found for the artist."),
            self._feature("current_lineup_presence", "Current lineup presence", has_current_year, 100.0 if has_current_year else 0.0, "nexus.lineup_appearance", "high", "Artist appears in the target edition lineup seed."),
            self._feature("genre_fit", "Hard-dance genre fit", primary_genre, genre_fit, "genre.v2.main_genre", "medium", "Genre fit based on V2.5 multi-genre classification."),
        ]

    def _metric_snapshot(self, artist_slug: str) -> MetricSnapshot:
        """Load all numeric metrics for one artist."""
        rows = list(
            self.db.scalars(select(ArtistMetricModel).where(ArtistMetricModel.artist_slug == artist_slug)).all()
        )
        numeric = {
            row.metric_key: float(row.metric_value_numeric)
            for row in rows
            if row.metric_value_numeric is not None
        }
        evidence_count = sum(max(int(row.evidence_count or 0), 0) for row in rows)
        return MetricSnapshot(numeric=numeric, evidence_count=evidence_count)

    def _metrics_by_artist(self, slugs: set[str]) -> dict[str, MetricSnapshot]:
        """Load metric snapshots in bulk for coverage counters."""
        if not slugs:
            return {}
        rows = list(self.db.scalars(select(ArtistMetricModel).where(ArtistMetricModel.artist_slug.in_(slugs))).all())
        grouped: dict[str, dict[str, float]] = {}
        counts: dict[str, int] = {}
        for row in rows:
            grouped.setdefault(row.artist_slug, {})
            counts[row.artist_slug] = counts.get(row.artist_slug, 0) + int(row.evidence_count or 0)
            if row.metric_value_numeric is not None:
                grouped[row.artist_slug][row.metric_key] = float(row.metric_value_numeric)
        return {slug: MetricSnapshot(numeric=metrics, evidence_count=counts.get(slug, 0)) for slug, metrics in grouped.items()}

    def _primary_genre(self, artist_slug: str, artist_payload: dict[str, Any]) -> str:
        """Return the V2.5 main genre, falling back to V1 seed."""
        row = self.db.scalar(
            select(ArtistGenreModel).where(ArtistGenreModel.artist_slug == artist_slug, ArtistGenreModel.is_primary.is_(True))
        )
        if row:
            return row.genre
        return str(artist_payload.get("primary_genre_seed") or "Unknown")

    def _secondary_genres(self, artist_slug: str) -> list[str]:
        """Return V2.5 secondary genre chips."""
        rows = list(
            self.db.scalars(
                select(ArtistGenreModel)
                .where(ArtistGenreModel.artist_slug == artist_slug, ArtistGenreModel.is_primary.is_(False))
                .order_by(ArtistGenreModel.rank.asc(), ArtistGenreModel.genre.asc())
            ).all()
        )
        return [row.genre for row in rows]

    @staticmethod
    def _metric(metrics: dict[str, float], keys: list[str]) -> float:
        """Return the first available metric value from an ordered key list."""
        for key in keys:
            if key in metrics:
                return float(metrics[key])
        return 0.0

    @staticmethod
    def _metric_contains(metrics: dict[str, float], required_fragments: list[str], optional_fragments: list[str]) -> float:
        """Return the maximum metric whose key contains the requested fragments."""
        values = []
        for key, value in metrics.items():
            lowered = key.lower()
            if all(fragment in lowered for fragment in required_fragments) and any(
                fragment in lowered for fragment in optional_fragments
            ):
                values.append(float(value))
        return max(values) if values else 0.0

    @staticmethod
    def _log_scale(value: float, target: float) -> float:
        """Normalize large counters without letting superstar counts dominate."""
        if value <= 0:
            return 0.0
        return round(min(100.0, math.log10(value + 1) / math.log10(target + 1) * 100.0), 2)

    @staticmethod
    def _weighted_average(values: list[tuple[float, float]]) -> float:
        """Return a weighted average of normalized values."""
        total_weight = sum(weight for _, weight in values)
        if total_weight <= 0:
            return 0.0
        return round(sum(value * weight for value, weight in values) / total_weight, 2)

    @staticmethod
    def _safe_json(raw: str | None, fallback: Any) -> Any:
        """Parse JSON from database text fields safely."""
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return fallback

    @staticmethod
    def _genre_fit(genre: str) -> float:
        """Translate genre confidence/context into a demand-fit feature."""
        if genre == "Unknown":
            return 35.0
        if genre in {"Classic / Legacy Hardstyle", "Rawstyle", "Xtra Raw", "Uptempo Hardcore", "Hardcore", "Frenchcore"}:
            return 88.0
        if genre in {"Euphoric Hardstyle", "Industrial Hardcore", "Mainstage Hard Dance"}:
            return 76.0
        return 62.0

    @staticmethod
    def _feature(
        key: str,
        label: str,
        raw_value: float | str | bool | None,
        normalized_value: float,
        source_metric: str,
        confidence: str,
        explanation: str,
    ) -> V2DemandFeature:
        """Create one feature with clamped normalized score."""
        return V2DemandFeature(
            key=key,
            label=label,
            value=raw_value,
            normalized_value=normalize_score(normalized_value),
            source_metric=source_metric,
            confidence=confidence,
            explanation=explanation,
        )

    @staticmethod
    def _fallback_used(features: list[V2DemandFeature]) -> bool:
        """Detect whether an artist relies mainly on internal fallback data."""
        external_groups = 0
        if any(feature.key.startswith("spotify") and feature.normalized_value > 0 for feature in features):
            external_groups += 1
        if any(feature.key.startswith("social") and feature.normalized_value > 0 for feature in features):
            external_groups += 1
        if any(feature.key.startswith("lastfm") and feature.normalized_value > 0 for feature in features):
            external_groups += 1
        if any(feature.key in {"career_event_count", "headliner_signals", "venue_prestige"} and feature.normalized_value > 0 for feature in features):
            external_groups += 1
        return external_groups < 2

    @staticmethod
    def _confidence(features: list[V2DemandFeature], *, fallback_used: bool, demand_score: float) -> str:
        """Estimate model confidence from feature coverage and demand strength."""
        non_zero = sum(1 for feature in features if feature.normalized_value > 0)
        if fallback_used and non_zero < 8:
            return "low"
        if non_zero >= 12 and demand_score >= 70:
            return "high"
        if non_zero >= 8:
            return "medium_high"
        return "medium"

    @staticmethod
    def _score_factors(
        *,
        popularity_score: float,
        career_score: float,
        momentum_score: float,
        nexus_affinity_score: float,
        genre: str,
        curated_prior_modifier: float,
    ) -> list[PredictionFactor]:
        """Build top-level factor explanations for the separated scores."""
        genre_modifier = GENRE_DEMAND_MODIFIERS.get(genre, 0.0)
        return [
            factor(
                "popularity_score",
                "Popularity score",
                popularity_score * SCORE_WEIGHTS["popularity_score"],
                30.0,
                "Spotify, Last.fm, social reach and music-platform presence are grouped into popularity.",
            ),
            factor(
                "career_score",
                "Career score",
                career_score * SCORE_WEIGHTS["career_score"],
                25.0,
                "External events, headliner signals, venue prestige and international reach drive career strength.",
            ),
            factor(
                "momentum_score",
                "Momentum score",
                momentum_score * SCORE_WEIGHTS["momentum_score"],
                20.0,
                "Social momentum, engagement, recent releases and Last.fm top tracks estimate current attention.",
            ),
            factor(
                "nexus_affinity_score",
                "Nexus affinity score",
                nexus_affinity_score * SCORE_WEIGHTS["nexus_affinity_score"],
                25.0,
                "Internal Nexus history and historical timetable data estimate local audience fit.",
            ),
            factor(
                "genre_modifier",
                "Genre modifier",
                genre_modifier,
                5.0,
                f"Main genre is {genre}; this adjusts demand using hard-dance context.",
            ),
            factor(
                "curated_high_demand_prior",
                "Curated high-demand prior",
                curated_prior_modifier,
                35.0,
                "Capped fallback prior for iconic or very high-interest acts until richer external labels are available.",
            ),
        ]

    @staticmethod
    def _explanations(slug: str, features: list[V2DemandFeature], *, demand_score: float, fallback_used: bool) -> list[str]:
        """Generate human-readable explanation bullets."""
        strongest = sorted(features, key=lambda item: item.normalized_value, reverse=True)[:4]
        explanations = [
            f"{feature.label}: {feature.normalized_value:.1f}/100 from {feature.source_metric}."
            for feature in strongest
            if feature.normalized_value > 0
        ]
        explanations.insert(0, f"{slug} receives a V2 demand score of {demand_score:.1f}/100.")
        if fallback_used:
            explanations.append("Fallback mode is active because external feature coverage is still incomplete.")
        return explanations

    @staticmethod
    def _notes(*, fallback_used: bool, primary_genre: str, features: list[V2DemandFeature]) -> list[str]:
        """Build model notes for the API."""
        notes = []
        if fallback_used:
            notes.append("Some external inputs are missing; internal Nexus and genre features keep the prediction available.")
        if primary_genre == "Unknown":
            notes.append("Genre is still Unknown, so demand is scored conservatively.")
        if not any(feature.key == "historical_timetable_slots" and feature.normalized_value > 0 for feature in features):
            notes.append("No historical timetable slot was found for this artist yet.")
        return notes

    def _ensure_predictions(self, year: int) -> None:
        """Rebuild lazily when no V2.7 predictions exist for the year."""
        count = self.db.scalar(
            select(func.count()).select_from(V2ArtistDemandPredictionModel).where(V2ArtistDemandPredictionModel.year == year)
        )
        if not count:
            self.rebuild(year, reset=True)

    def _row_to_schema(self, row: V2ArtistDemandPredictionModel) -> V2DemandPrediction:
        """Convert one ORM row to its public schema."""
        features = [V2DemandFeature(**item) for item in self._safe_json(row.feature_payload_json, [])]
        factors = [PredictionFactor(**item) for item in self._safe_json(row.factor_payload_json, [])]
        explanations = list(self._safe_json(row.explanation_json, []))
        secondary_genres = list(self._safe_json(row.secondary_genres_json, []))
        notes = [line for line in (row.notes or "").splitlines() if line]
        generated = row.generated_at.replace(tzinfo=timezone.utc).isoformat() if row.generated_at else ""
        return V2DemandPrediction(
            year=row.year,
            artist_slug=row.artist_slug,
            artist_name=row.artist_name,
            rank=row.rank,
            main_genre=row.main_genre,
            secondary_genres=secondary_genres,
            popularity_score=round(row.popularity_score, 2),
            career_score=round(row.career_score, 2),
            momentum_score=round(row.momentum_score, 2),
            nexus_affinity_score=round(row.nexus_affinity_score, 2),
            demand_score=round(row.demand_score, 2),
            crowd_risk=row.crowd_risk,
            confidence=row.confidence,
            model_version=row.model_version,
            method=row.method,
            fallback_used=row.fallback_used,
            evidence_count=row.evidence_count,
            features=features,
            factors=factors,
            explanations=explanations,
            notes=notes,
            generated_at=generated,
        )

    @staticmethod
    def _main_comparison_reason(row: V2ArtistDemandPredictionModel, old_score: float | None) -> str:
        """Explain the biggest V1/V2 change in one sentence."""
        if old_score is None:
            return "No V1 score was available for comparison."
        delta = row.demand_score - old_score
        if abs(delta) < 5:
            return "V2 stays close to V1 because internal and external signals agree."
        if delta > 0:
            return "V2 raises the artist because external popularity/career evidence strengthens the internal score."
        return "V2 lowers the artist because evidence coverage or external momentum is weaker than the V1 manual hype estimate."
