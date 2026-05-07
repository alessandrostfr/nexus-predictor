"""Import V1 JSON and seed data into the V2 evidence layer.

This module intentionally treats the V1 dataset as evidence, not as final truth.
Every imported value records source, confidence and extraction method so later
blocks can compare it against Spotify, social metrics, event crawlers and manual
corrections.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from slugify import slugify
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ArtistMetricModel,
    ArtistModel,
    CareerEventModel,
    EvidenceItemModel,
    PlatformProfileModel,
    SocialProfileModel,
    SourceModel,
    VenuePrestigeModel,
)
from app.repositories.json_repository import JsonSeedRepository
from app.services.database_seed_service import dumps_json, is_database_seeded, seed_database_from_json

json_repository = JsonSeedRepository()


DEFAULT_SOURCES: list[dict[str, Any]] = [
    {
        "key": "internal_nexus_dataset",
        "name": "Internal Nexus V1 dataset",
        "source_type": "internal_dataset",
        "base_url": None,
        "default_confidence": "high",
        "extraction_method": "json_seed",
        "notes": "Normalized V1 JSON dataset created from researched lineups and manual review.",
    },
    {
        "key": "internal_artist_index",
        "name": "Internal artist index V1",
        "source_type": "internal_dataset",
        "base_url": None,
        "default_confidence": "high",
        "extraction_method": "json_seed",
        "notes": "Artist index generated from historical Nexus lineups.",
    },
    {
        "key": "internal_genre_seed",
        "name": "Internal V1 genre seed",
        "source_type": "internal_dataset",
        "base_url": None,
        "default_confidence": "medium",
        "extraction_method": "computed",
        "notes": "Transparent V1 genre seed. It is useful evidence, not a final V2 multi-genre truth.",
    },
    {
        "key": "internal_venue_seed",
        "name": "Internal Fabrik venue seed",
        "source_type": "internal_dataset",
        "base_url": None,
        "default_confidence": "medium",
        "extraction_method": "json_seed",
        "notes": "Editable room/capacity seed used by V1 room-risk features.",
    },
    {
        "key": "manual_user_evidence",
        "name": "User-provided manual evidence",
        "source_type": "manual_evidence",
        "base_url": None,
        "default_confidence": "verified",
        "extraction_method": "user_evidence",
        "notes": "Manual evidence supplied by the project owner, including direct attendance knowledge and schedule images.",
    },
]


def now_utc() -> datetime:
    """Return a naive UTC datetime compatible with current project DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_confidence(value: str | None, *, fallback: str = "medium") -> str:
    """Map V1 confidence values to the closed V2 confidence model."""
    if not value:
        return fallback

    cleaned = value.lower().strip().replace("-", "_")
    if cleaned in {"verified", "official"}:
        return "verified"
    if cleaned in {"high", "visual_reference"}:
        return "high"
    if cleaned in {"medium", "medium_high", "medium_low"}:
        return "medium"
    if cleaned in {"low", "low_medium", "pending", "unknown"}:
        return "low"
    return fallback


def infer_source_type(source_key: str) -> str:
    """Infer source type from existing V1 source keys."""
    key = source_key.lower()
    if key.startswith("ra_") or "resident" in key:
        return "event_listing"
    if "fabrik" in key:
        return "venue_official"
    if "ticket" in key or "rebel" in key:
        return "ticketing"
    if key.startswith("user"):
        return "manual_evidence"
    if "capacity" in key:
        return "venue_research"
    return "public_web"


def get_or_create_source(
    db: Session,
    *,
    key: str,
    name: str,
    source_type: str,
    base_url: str | None = None,
    confidence: str = "medium",
    extraction_method: str = "json_seed",
    notes: str | None = None,
    raw: dict[str, Any] | None = None,
) -> SourceModel:
    """Insert or update a source registry row by stable key."""
    source = db.scalar(select(SourceModel).where(SourceModel.key == key))
    if source is None:
        source = SourceModel(
            key=key,
            name=name,
            source_type=source_type,
            base_url=base_url,
            default_confidence=normalize_confidence(confidence),
            extraction_method=extraction_method,
            notes=notes,
            raw_json=dumps_json(raw or {}),
        )
        db.add(source)
        db.flush()
        return source

    source.name = name
    source.source_type = source_type
    source.base_url = base_url
    source.default_confidence = normalize_confidence(confidence, fallback=source.default_confidence)
    source.extraction_method = extraction_method
    source.notes = notes or source.notes
    source.raw_json = dumps_json(raw or {})
    return source


def ensure_source_registry(db: Session) -> dict[str, SourceModel]:
    """Seed sources from defaults and from edition/venue JSON source arrays."""
    sources: dict[str, SourceModel] = {}

    for source in DEFAULT_SOURCES:
        sources[source["key"]] = get_or_create_source(
            db,
            key=source["key"],
            name=source["name"],
            source_type=source["source_type"],
            base_url=source["base_url"],
            confidence=source["default_confidence"],
            extraction_method=source["extraction_method"],
            notes=source["notes"],
            raw=source,
        )

    for edition in json_repository.list_editions():
        for source in edition.get("sources", []):
            key = source.get("key") or slugify(source.get("name", "edition-source"))
            sources[key] = get_or_create_source(
                db,
                key=key,
                name=source.get("name", key),
                source_type=infer_source_type(key),
                base_url=source.get("url"),
                confidence=source.get("confidence", "medium"),
                extraction_method="json_seed",
                notes=f"Source declared in Nexus {edition.get('year')} JSON seed.",
                raw={"edition_year": edition.get("year"), **source},
            )

    venue_seed = json_repository.get_venue()
    for source in venue_seed.get("sources", []):
        key = source.get("source") or source.get("key") or slugify(source.get("name", "venue-source"))
        sources[key] = get_or_create_source(
            db,
            key=key,
            name=source.get("name") or source.get("source") or key,
            source_type=infer_source_type(key),
            base_url=source.get("url"),
            confidence=source.get("confidence", "medium"),
            extraction_method="json_seed",
            notes=source.get("notes", "Source declared in Fabrik venue JSON seed."),
            raw=source,
        )

    return sources


def get_source(sources: dict[str, SourceModel], key: str, fallback: str = "internal_nexus_dataset") -> SourceModel:
    """Return a source by key, falling back to a safe internal source."""
    return sources.get(key) or sources[fallback]


def create_evidence(
    db: Session,
    *,
    artist: ArtistModel | None,
    source: SourceModel,
    metric_key: str,
    metric_value: Any,
    value_type: str = "text",
    confidence: str | None = None,
    extraction_method: str | None = None,
    evidence_kind: str = "metric",
    status: str = "confirmed",
    notes: str | None = None,
    source_url: str | None = None,
    raw: dict[str, Any] | None = None,
) -> EvidenceItemModel:
    """Create a single evidence item with normalized defaults."""
    item = EvidenceItemModel(
        artist_id=artist.id if artist else None,
        artist_slug=artist.slug if artist else None,
        source_id=source.id,
        source_type=source.source_type,
        source_name=source.name,
        source_url=source_url or source.base_url,
        captured_at=now_utc(),
        metric_key=metric_key,
        metric_value=json.dumps(metric_value, ensure_ascii=False) if isinstance(metric_value, (dict, list)) else str(metric_value),
        value_type=value_type,
        confidence=normalize_confidence(confidence or source.default_confidence),
        extraction_method=extraction_method or source.extraction_method,
        evidence_kind=evidence_kind,
        status=status,
        notes=notes,
        raw_json=dumps_json(raw or {}),
    )
    db.add(item)
    db.flush()
    return item


def upsert_artist_metric(
    db: Session,
    *,
    artist: ArtistModel,
    metric_key: str,
    numeric_value: float | None = None,
    text_value: str | None = None,
    value_type: str = "number",
    confidence: str = "medium",
    evidence_count: int = 0,
    notes: str | None = None,
    raw: dict[str, Any] | None = None,
) -> ArtistMetricModel:
    """Insert or update a derived artist metric."""
    metric = db.scalar(
        select(ArtistMetricModel).where(
            ArtistMetricModel.artist_slug == artist.slug,
            ArtistMetricModel.metric_key == metric_key,
        )
    )
    if metric is None:
        metric = ArtistMetricModel(
            artist_id=artist.id,
            artist_slug=artist.slug,
            metric_key=metric_key,
            metric_value_numeric=numeric_value,
            metric_value_text=text_value,
            value_type=value_type,
            confidence=normalize_confidence(confidence),
            evidence_count=evidence_count,
            latest_captured_at=now_utc(),
            notes=notes,
            raw_json=dumps_json(raw or {}),
        )
        db.add(metric)
        db.flush()
        return metric

    metric.metric_value_numeric = numeric_value
    metric.metric_value_text = text_value
    metric.value_type = value_type
    metric.confidence = normalize_confidence(confidence)
    metric.evidence_count = evidence_count
    metric.latest_captured_at = now_utc()
    metric.notes = notes
    metric.raw_json = dumps_json(raw or {})
    return metric


def reset_evidence_layer(db: Session) -> None:
    """Delete only V2 evidence-layer data, preserving V1 seed tables."""
    for model in (
        VenuePrestigeModel,
        CareerEventModel,
        SocialProfileModel,
        PlatformProfileModel,
        ArtistMetricModel,
        EvidenceItemModel,
        SourceModel,
    ):
        db.execute(delete(model))
    db.flush()


def import_artist_seed_evidence(
    db: Session,
    *,
    sources: dict[str, SourceModel],
) -> dict[str, int]:
    """Create evidence rows and base metrics for every V1 artist."""
    artists = list(db.scalars(select(ArtistModel).order_by(ArtistModel.slug)))
    inserted_evidence = 0
    inserted_metrics = 0

    artist_index_source = sources["internal_artist_index"]
    genre_source = sources["internal_genre_seed"]

    for artist in artists:
        create_evidence(
            db,
            artist=artist,
            source=artist_index_source,
            metric_key="nexus.appearance_count",
            metric_value=artist.appearance_count,
            value_type="number",
            confidence="high",
            notes="Appearance count imported from the normalized V1 artist index.",
            raw={"artist_slug": artist.slug},
        )
        inserted_evidence += 1

        create_evidence(
            db,
            artist=artist,
            source=artist_index_source,
            metric_key="nexus.appearance_years",
            metric_value=json.loads(artist.appearance_years_json or "[]"),
            value_type="json",
            confidence="high",
            notes="Years in which the artist appears in the V1 Nexus dataset.",
            raw={"artist_slug": artist.slug},
        )
        inserted_evidence += 1

        genre_confidence = "low" if artist.primary_genre_seed == "Unknown" else "medium"
        create_evidence(
            db,
            artist=artist,
            source=genre_source,
            metric_key="genre.v1_primary_genre_seed",
            metric_value=artist.primary_genre_seed,
            value_type="text",
            confidence=genre_confidence,
            status="pending_review" if artist.primary_genre_seed == "Unknown" else "inferred",
            notes="V1 single-genre seed. V2.5 will replace this with multi-genre evidence.",
            raw={"artist_slug": artist.slug, "primary_genre_seed": artist.primary_genre_seed},
        )
        inserted_evidence += 1

        appearances = json.loads(artist.appearances_json or "[]")
        for appearance in appearances:
            source_key = appearance.get("source_key") or "internal_nexus_dataset"
            source = get_source(sources, source_key)
            create_evidence(
                db,
                artist=artist,
                source=source,
                metric_key="nexus.lineup_appearance",
                metric_value={
                    "year": appearance.get("year"),
                    "performance_display_name": appearance.get("performance_display_name"),
                    "performance_type": appearance.get("performance_type"),
                },
                value_type="json",
                confidence=source.default_confidence,
                notes="Artist appearance imported from V1 lineup seed.",
                raw=appearance,
            )
            inserted_evidence += 1

            if appearance.get("year"):
                db.add(
                    CareerEventModel(
                        artist_id=artist.id,
                        artist_slug=artist.slug,
                        event_name=f"Nexus Festival {appearance.get('year')}",
                        event_type="festival_lineup",
                        role=appearance.get("performance_type") or "artist",
                        country="Spain",
                        city="Humanes de Madrid",
                        venue_name="Fabrik Madrid",
                        event_date=None,
                        year=int(appearance.get("year")),
                        is_headliner=False,
                        confidence=normalize_confidence(source.default_confidence),
                        source_id=source.id,
                        raw_json=dumps_json(appearance),
                    )
                )

        upsert_artist_metric(
            db,
            artist=artist,
            metric_key="nexus_appearance_count",
            numeric_value=float(artist.appearance_count),
            value_type="number",
            confidence="high",
            evidence_count=max(1, len(appearances)),
            notes="Base V2 feature imported from V1 historical appearances.",
        )
        inserted_metrics += 1

        upsert_artist_metric(
            db,
            artist=artist,
            metric_key="v1_primary_genre_seed",
            text_value=artist.primary_genre_seed,
            value_type="text",
            confidence=genre_confidence,
            evidence_count=1,
            notes="Temporary genre feature until V2.5 multi-genre classification.",
        )
        inserted_metrics += 1

    return {"artists": len(artists), "evidence_items": inserted_evidence, "artist_metrics": inserted_metrics}


def import_venue_prestige_seed(db: Session, *, sources: dict[str, SourceModel]) -> int:
    """Create initial prestige entries for Fabrik rooms from the V1 venue seed."""
    venue_seed = json_repository.get_venue()
    source = sources["internal_venue_seed"]
    inserted = 0

    rooms = venue_seed.get("rooms", []) or venue_seed.get("areas", [])
    for room in rooms:
        name = room.get("name")
        if not name:
            continue
        slug = room.get("slug") or slugify(name)
        existing = db.scalar(select(VenuePrestigeModel).where(VenuePrestigeModel.slug == slug))
        estimated_capacity = room.get("estimated_capacity") or room.get("capacity")
        capacity_score = min(float(estimated_capacity or 0) / 1000.0, 10.0)
        prestige_score = max(1.0, round(capacity_score, 2))
        if existing is None:
            db.add(
                VenuePrestigeModel(
                    slug=slug,
                    name=name,
                    venue_type="fabrik_room",
                    city="Humanes de Madrid",
                    country="Spain",
                    capacity=estimated_capacity,
                    prestige_score=prestige_score,
                    confidence=normalize_confidence(room.get("confidence", "medium")),
                    source_id=source.id,
                    notes="Initial prestige seed from V1 room/capacity data. It will be refined in later V2 blocks.",
                    raw_json=dumps_json(room),
                )
            )
            inserted += 1

    return inserted


def import_v1_evidence_layer(db: Session, *, reset: bool = False) -> dict[str, int]:
    """Import V1 JSON-backed data into the V2 evidence model."""
    if not is_database_seeded(db):
        seed_database_from_json(db, reset=False)

    if reset:
        reset_evidence_layer(db)
    elif db.scalar(select(func.count()).select_from(EvidenceItemModel)):
        return get_evidence_seed_status(db)

    sources = ensure_source_registry(db)
    artist_result = import_artist_seed_evidence(db, sources=sources)
    venue_prestige_items = import_venue_prestige_seed(db, sources=sources)
    db.commit()

    return {
        "sources": len(sources),
        "venue_prestige_items": venue_prestige_items,
        **artist_result,
    }


def ensure_v2_evidence_ready(db: Session) -> None:
    """Ensure V2.1 evidence data exists without repeatedly reseeding it."""
    evidence_count = int(db.scalar(select(func.count()).select_from(EvidenceItemModel)) or 0)
    if evidence_count == 0:
        import_v1_evidence_layer(db, reset=False)


def get_evidence_seed_status(db: Session) -> dict[str, int]:
    """Return import counts for validation scripts."""
    return {
        "sources": int(db.scalar(select(func.count()).select_from(SourceModel)) or 0),
        "evidence_items": int(db.scalar(select(func.count()).select_from(EvidenceItemModel)) or 0),
        "artist_metrics": int(db.scalar(select(func.count()).select_from(ArtistMetricModel)) or 0),
        "career_events": int(db.scalar(select(func.count()).select_from(CareerEventModel)) or 0),
        "venue_prestige_items": int(db.scalar(select(func.count()).select_from(VenuePrestigeModel)) or 0),
    }
