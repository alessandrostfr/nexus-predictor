"""Read and write services for the V2 evidence layer."""

from __future__ import annotations

from sqlalchemy import distinct, func, select
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
from app.schemas.evidence import CreateManualEvidenceRequest
from app.services.evidence_seed_service import create_evidence, get_or_create_source, normalize_confidence


class EvidenceService:
    """High-level operations used by evidence API endpoints."""

    def __init__(self, db: Session) -> None:
        """Store the request-scoped database session."""
        self.db = db

    def list_sources(self) -> list[SourceModel]:
        """Return active and inactive sources sorted by type/name."""
        return list(
            self.db.scalars(
                select(SourceModel).order_by(SourceModel.source_type.asc(), SourceModel.name.asc())
            )
        )

    def get_coverage(self) -> dict[str, int]:
        """Return evidence coverage counts for validation and UI diagnostics."""
        artists = int(self.db.scalar(select(func.count()).select_from(ArtistModel)) or 0)
        artists_with_evidence = int(
            self.db.scalar(select(func.count(distinct(EvidenceItemModel.artist_slug)))) or 0
        )
        return {
            "artists": artists,
            "artists_with_evidence": artists_with_evidence,
            "sources": int(self.db.scalar(select(func.count()).select_from(SourceModel)) or 0),
            "evidence_items": int(self.db.scalar(select(func.count()).select_from(EvidenceItemModel)) or 0),
            "artist_metrics": int(self.db.scalar(select(func.count()).select_from(ArtistMetricModel)) or 0),
            "platform_profiles": int(self.db.scalar(select(func.count()).select_from(PlatformProfileModel)) or 0),
            "social_profiles": int(self.db.scalar(select(func.count()).select_from(SocialProfileModel)) or 0),
            "career_events": int(self.db.scalar(select(func.count()).select_from(CareerEventModel)) or 0),
            "venue_prestige_items": int(self.db.scalar(select(func.count()).select_from(VenuePrestigeModel)) or 0),
        }

    def get_artist_overview(self, artist_slug: str, *, limit: int = 100) -> dict[str, object] | None:
        """Return evidence, metrics and profile shells for one artist."""
        artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == artist_slug))
        if artist is None:
            return None

        evidence_items = list(
            self.db.scalars(
                select(EvidenceItemModel)
                .where(EvidenceItemModel.artist_slug == artist_slug)
                .order_by(EvidenceItemModel.created_at.desc(), EvidenceItemModel.id.desc())
                .limit(limit)
            )
        )
        metrics = list(
            self.db.scalars(
                select(ArtistMetricModel)
                .where(ArtistMetricModel.artist_slug == artist_slug)
                .order_by(ArtistMetricModel.metric_key.asc())
            )
        )
        platform_profiles = list(
            self.db.scalars(
                select(PlatformProfileModel)
                .where(PlatformProfileModel.artist_slug == artist_slug)
                .order_by(PlatformProfileModel.platform.asc())
            )
        )
        social_profiles = list(
            self.db.scalars(
                select(SocialProfileModel)
                .where(SocialProfileModel.artist_slug == artist_slug)
                .order_by(SocialProfileModel.platform.asc())
            )
        )
        career_events = list(
            self.db.scalars(
                select(CareerEventModel)
                .where(CareerEventModel.artist_slug == artist_slug)
                .order_by(CareerEventModel.year.desc(), CareerEventModel.event_name.asc())
            )
        )

        return {
            "artist_slug": artist.slug,
            "artist_name": artist.name,
            "evidence_items": evidence_items,
            "metrics": metrics,
            "platform_profiles": platform_profiles,
            "social_profiles": social_profiles,
            "career_events": career_events,
        }

    def list_artist_metrics(self, artist_slug: str) -> list[ArtistMetricModel] | None:
        """Return derived metrics for one artist or None when the artist is missing."""
        artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == artist_slug))
        if artist is None:
            return None
        return list(
            self.db.scalars(
                select(ArtistMetricModel)
                .where(ArtistMetricModel.artist_slug == artist_slug)
                .order_by(ArtistMetricModel.metric_key.asc())
            )
        )

    def list_venue_prestige(self) -> list[VenuePrestigeModel]:
        """Return venue/festival prestige seed rows."""
        return list(
            self.db.scalars(
                select(VenuePrestigeModel).order_by(
                    VenuePrestigeModel.prestige_score.desc(),
                    VenuePrestigeModel.name.asc(),
                )
            )
        )

    def create_manual_evidence(self, payload: CreateManualEvidenceRequest) -> EvidenceItemModel | None:
        """Register user-provided evidence with explicit confidence and notes."""
        artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == payload.artist_slug))
        if artist is None:
            return None

        source = get_or_create_source(
            self.db,
            key="manual_user_evidence",
            name=payload.source_name,
            source_type="manual_evidence",
            base_url=payload.source_url,
            confidence=payload.confidence,
            extraction_method="user_evidence",
            notes="Manual evidence supplied by the project owner or validated from uploaded images.",
            raw=payload.model_dump(),
        )
        evidence = create_evidence(
            self.db,
            artist=artist,
            source=source,
            metric_key=payload.metric_key,
            metric_value=payload.metric_value,
            value_type="text",
            confidence=normalize_confidence(payload.confidence),
            extraction_method="user_evidence",
            evidence_kind="manual_fact",
            status=payload.status,
            notes=payload.notes,
            source_url=payload.source_url,
            raw=payload.model_dump(),
        )
        self.db.commit()
        self.db.refresh(evidence)
        return evidence
