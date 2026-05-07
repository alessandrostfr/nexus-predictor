"""External ingestion service for V2.3.

The first external-ingestion block intentionally favours a safe, traceable and
reviewable pipeline over fragile scraping. It loads a curated public-research
seed, registers source metadata, persists candidate career events, creates
venue/festival prestige rows and derives coverage metrics.

Rows collected automatically or semi-automatically are stored with low/medium
confidence until they are reviewed. This matches the V2 requirement that doubtful
public data should not be treated as absolute truth.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from slugify import slugify
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.paths import EXTERNAL_RESEARCH_SEED_PATH
from app.db.models import (
    ArtistMetricModel,
    ArtistModel,
    CareerEventModel,
    EvidenceItemModel,
    SourceModel,
    VenuePrestigeModel,
)
from app.services.database_seed_service import dumps_json, loads_json, seed_database_from_json
from app.services.evidence_seed_service import (
    create_evidence,
    get_or_create_source,
    normalize_confidence,
    upsert_artist_metric,
)


EXTERNAL_SOURCE_PREFIX = "v2_external_"
EXTERNAL_METRIC_PREFIX = "external."


class ExternalIngestionService:
    """Persist V2.3 external research data into the evidence layer."""

    def __init__(self, db: Session, seed_path: Path = EXTERNAL_RESEARCH_SEED_PATH) -> None:
        """Store a SQLAlchemy session and the JSON seed path."""
        self.db = db
        self.seed_path = seed_path

    def load_seed(self) -> dict[str, Any]:
        """Load the curated external-research seed from disk."""
        if not self.seed_path.exists():
            raise FileNotFoundError(f"External ingestion seed was not found: {self.seed_path}")

        with self.seed_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def ensure_artist_seed(self) -> None:
        """Ensure V1-compatible artist rows exist before external ingestion."""
        artist_count = int(self.db.scalar(select(func.count()).select_from(ArtistModel)) or 0)
        if artist_count == 0:
            seed_database_from_json(self.db, reset=True)

    def reset_external_ingestion_data(self, seed: dict[str, Any]) -> None:
        """Delete previous V2.3 rows without touching V2.1/V2.2 data."""
        source_keys = [source["key"] for source in seed.get("sources", [])]
        source_ids = list(
            self.db.scalars(
                select(SourceModel.id).where(SourceModel.key.in_(source_keys))
            )
        )

        if source_ids:
            self.db.execute(
                delete(CareerEventModel).where(CareerEventModel.source_id.in_(source_ids))
            )
            self.db.execute(
                delete(EvidenceItemModel).where(EvidenceItemModel.source_id.in_(source_ids))
            )

        self.db.execute(
            delete(ArtistMetricModel).where(
                ArtistMetricModel.metric_key.like(f"{EXTERNAL_METRIC_PREFIX}%")
            )
        )

        venue_slugs = [venue["slug"] for venue in seed.get("venue_catalog", [])]
        if venue_slugs:
            self.db.execute(delete(VenuePrestigeModel).where(VenuePrestigeModel.slug.in_(venue_slugs)))

        self.db.commit()

    def ensure_sources(self, seed: dict[str, Any]) -> dict[str, SourceModel]:
        """Register or update external source rows."""
        sources: dict[str, SourceModel] = {}
        for source in seed.get("sources", []):
            sources[source["key"]] = get_or_create_source(
                self.db,
                key=source["key"],
                name=source["name"],
                source_type=source["source_type"],
                base_url=source.get("base_url"),
                confidence=source.get("default_confidence", "medium"),
                extraction_method=source.get("extraction_method", "prefect_seed"),
                notes=source.get("notes"),
                raw=source,
            )
        self.db.flush()
        return sources

    def upsert_venue_catalog(self, seed: dict[str, Any], sources: dict[str, SourceModel]) -> int:
        """Insert or update venue/festival prestige rows."""
        count = 0
        for venue in seed.get("venue_catalog", []):
            source = sources.get(venue.get("source_key")) or next(iter(sources.values()))
            existing = self.db.scalar(
                select(VenuePrestigeModel).where(VenuePrestigeModel.slug == venue["slug"])
            )
            evidence = create_evidence(
                self.db,
                artist=None,
                source=source,
                metric_key="external.venue_prestige",
                metric_value={
                    "slug": venue["slug"],
                    "name": venue["name"],
                    "prestige_score": venue["prestige_score"],
                    "venue_type": venue.get("venue_type"),
                },
                value_type="json",
                confidence=venue.get("confidence", source.default_confidence),
                extraction_method="prefect_seed",
                evidence_kind="venue_prestige",
                status="pending_review" if venue.get("confidence") != "verified" else "confirmed",
                notes=venue.get("notes"),
                source_url=venue.get("source_url"),
                raw=venue,
            )

            if existing is None:
                existing = VenuePrestigeModel(
                    slug=venue["slug"],
                    name=venue["name"],
                    venue_type=venue.get("venue_type", "venue"),
                    city=venue.get("city"),
                    country=venue.get("country"),
                    capacity=venue.get("capacity"),
                    prestige_score=float(venue.get("prestige_score", 0.0)),
                    confidence=normalize_confidence(venue.get("confidence", "medium")),
                    source_id=source.id,
                    evidence_id=evidence.id,
                    notes=venue.get("notes"),
                    raw_json=dumps_json(venue),
                )
                self.db.add(existing)
            else:
                existing.name = venue["name"]
                existing.venue_type = venue.get("venue_type", existing.venue_type)
                existing.city = venue.get("city")
                existing.country = venue.get("country")
                existing.capacity = venue.get("capacity")
                existing.prestige_score = float(venue.get("prestige_score", existing.prestige_score))
                existing.confidence = normalize_confidence(venue.get("confidence", existing.confidence))
                existing.source_id = source.id
                existing.evidence_id = evidence.id
                existing.notes = venue.get("notes")
                existing.raw_json = dumps_json(venue)

            count += 1

        self.db.flush()
        return count

    def create_career_events(
        self,
        seed: dict[str, Any],
        sources: dict[str, SourceModel],
        *,
        limit_artists: int | None = None,
    ) -> tuple[int, int, int]:
        """Persist candidate career events and return counts.

        Returns:
            Tuple of inserted career events, evidence items and skipped rows.
        """
        inserted_events = 0
        evidence_items = 0
        skipped_unknown_artists = 0

        seen_artists: set[str] = set()
        for signal in seed.get("artist_career_signals", []):
            artist_slug = signal["artist_slug"]
            if limit_artists is not None and artist_slug not in seen_artists and len(seen_artists) >= limit_artists:
                continue

            artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == artist_slug))
            if artist is None:
                skipped_unknown_artists += 1
                continue

            seen_artists.add(artist_slug)
            source = sources.get(signal.get("source_key")) or next(iter(sources.values()))

            duplicate = self.db.scalar(
                select(CareerEventModel).where(
                    CareerEventModel.artist_slug == artist_slug,
                    CareerEventModel.event_name == signal["event_name"],
                    CareerEventModel.source_id == source.id,
                )
            )
            if duplicate is not None:
                continue

            evidence = create_evidence(
                self.db,
                artist=artist,
                source=source,
                metric_key="external.career_event",
                metric_value={
                    "event_name": signal["event_name"],
                    "event_type": signal.get("event_type", "festival"),
                    "role": signal.get("role"),
                    "country": signal.get("country"),
                    "is_headliner": bool(signal.get("is_headliner", False)),
                },
                value_type="json",
                confidence=signal.get("confidence", "low"),
                extraction_method="prefect_seed",
                evidence_kind="career_event",
                status="pending_review",
                notes=signal.get("notes"),
                source_url=signal.get("source_url"),
                raw=signal,
            )
            event = CareerEventModel(
                artist_id=artist.id,
                artist_slug=artist.slug,
                event_name=signal["event_name"],
                event_type=signal.get("event_type", "festival"),
                role=signal.get("role"),
                country=signal.get("country"),
                city=signal.get("city"),
                venue_name=signal.get("venue_name"),
                event_date=signal.get("event_date"),
                year=signal.get("year"),
                is_headliner=bool(signal.get("is_headliner", False)),
                confidence=normalize_confidence(signal.get("confidence", "low")),
                source_id=source.id,
                evidence_id=evidence.id,
                raw_json=dumps_json(signal),
            )
            self.db.add(event)
            inserted_events += 1
            evidence_items += 1

        self.db.flush()
        return inserted_events, evidence_items, skipped_unknown_artists

    def update_artist_external_metrics(self) -> int:
        """Derive per-artist V2.3 metrics from external career events."""
        rows = list(
            self.db.execute(
                select(CareerEventModel.artist_slug, CareerEventModel)
                .join(SourceModel, CareerEventModel.source_id == SourceModel.id)
                .where(SourceModel.key.like(f"{EXTERNAL_SOURCE_PREFIX}%"))
            )
        )

        events_by_artist: dict[str, list[CareerEventModel]] = defaultdict(list)
        for artist_slug, event in rows:
            events_by_artist[artist_slug].append(event)

        upserted = 0
        for artist_slug, events in events_by_artist.items():
            artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == artist_slug))
            if artist is None:
                continue

            countries = {event.country for event in events if event.country}
            headliner_count = sum(1 for event in events if event.is_headliner)
            event_count = len(events)
            prestige_values = self._prestige_values_for_events(events)
            max_prestige = max(prestige_values) if prestige_values else None

            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key="external.career_event_count",
                numeric_value=float(event_count),
                value_type="number",
                confidence="low",
                evidence_count=event_count,
                notes="Number of V2.3 candidate external career events queued for review.",
                raw={"events": [event.event_name for event in events]},
            )
            upserted += 1

            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key="external.headliner_signal_count",
                numeric_value=float(headliner_count),
                value_type="number",
                confidence="low",
                evidence_count=headliner_count,
                notes="Count of candidate headliner or main-stage signals from V2.3 ingestion.",
                raw={"headliner_events": [event.event_name for event in events if event.is_headliner]},
            )
            upserted += 1

            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key="external.country_count",
                numeric_value=float(len(countries)),
                value_type="number",
                confidence="low",
                evidence_count=len(countries),
                notes="Number of countries represented by candidate V2.3 career signals.",
                raw={"countries": sorted(countries)},
            )
            upserted += 1

            if max_prestige is not None:
                upsert_artist_metric(
                    self.db,
                    artist=artist,
                    metric_key="external.max_venue_prestige_signal",
                    numeric_value=float(max_prestige),
                    value_type="number",
                    confidence="medium",
                    evidence_count=len(prestige_values),
                    notes="Maximum prestige score among venues/festivals linked by V2.3 candidate events.",
                    raw={"prestige_values": prestige_values},
                )
                upserted += 1

        self.db.flush()
        return upserted

    def _prestige_values_for_events(self, events: list[CareerEventModel]) -> list[float]:
        """Return prestige scores matched by venue/festival names."""
        values: list[float] = []
        for event in events:
            candidates = [event.venue_name, event.event_name]
            for candidate in candidates:
                if not candidate:
                    continue
                slug = slugify(candidate)
                venue = self.db.scalar(select(VenuePrestigeModel).where(VenuePrestigeModel.slug == slug))
                if venue:
                    values.append(float(venue.prestige_score))
                    break
        return values

    def coverage(self) -> dict[str, int]:
        """Return V2.3 external-ingestion coverage counts."""
        external_source_ids = list(
            self.db.scalars(select(SourceModel.id).where(SourceModel.key.like(f"{EXTERNAL_SOURCE_PREFIX}%")))
        )
        if not external_source_ids:
            return {
                "external_sources": 0,
                "external_evidence_items": 0,
                "external_career_events": 0,
                "external_artist_metrics": 0,
                "artists_with_external_events": 0,
                "artists_with_headliner_signals": 0,
                "venue_prestige_items": int(self.db.scalar(select(func.count()).select_from(VenuePrestigeModel)) or 0),
            }

        return {
            "external_sources": len(external_source_ids),
            "external_evidence_items": int(
                self.db.scalar(
                    select(func.count()).select_from(EvidenceItemModel).where(EvidenceItemModel.source_id.in_(external_source_ids))
                )
                or 0
            ),
            "external_career_events": int(
                self.db.scalar(
                    select(func.count()).select_from(CareerEventModel).where(CareerEventModel.source_id.in_(external_source_ids))
                )
                or 0
            ),
            "external_artist_metrics": int(
                self.db.scalar(
                    select(func.count()).select_from(ArtistMetricModel).where(
                        ArtistMetricModel.metric_key.like(f"{EXTERNAL_METRIC_PREFIX}%")
                    )
                )
                or 0
            ),
            "artists_with_external_events": int(
                self.db.scalar(
                    select(func.count(func.distinct(CareerEventModel.artist_slug))).where(
                        CareerEventModel.source_id.in_(external_source_ids)
                    )
                )
                or 0
            ),
            "artists_with_headliner_signals": int(
                self.db.scalar(
                    select(func.count(func.distinct(CareerEventModel.artist_slug))).where(
                        CareerEventModel.source_id.in_(external_source_ids),
                        CareerEventModel.is_headliner.is_(True),
                    )
                )
                or 0
            ),
            "venue_prestige_items": int(self.db.scalar(select(func.count()).select_from(VenuePrestigeModel)) or 0),
        }

    def run(
        self,
        *,
        reset: bool = False,
        limit_artists: int | None = None,
    ) -> dict[str, Any]:
        """Execute the deterministic V2.3 ingestion pipeline."""
        self.ensure_artist_seed()
        seed = self.load_seed()

        if reset:
            self.reset_external_ingestion_data(seed)

        sources = self.ensure_sources(seed)
        venue_count = self.upsert_venue_catalog(seed, sources)
        career_events, evidence_items, skipped_unknown = self.create_career_events(
            seed,
            sources,
            limit_artists=limit_artists,
        )
        metric_count = self.update_artist_external_metrics()

        self.db.commit()

        return {
            "sources": len(sources),
            "venue_prestige_items": venue_count,
            "career_events": career_events,
            "evidence_items": evidence_items + venue_count,
            "artist_metrics": metric_count,
            "skipped_unknown_artists": skipped_unknown,
            "warnings": [],
        }
