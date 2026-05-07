"""Social and music-platform ingestion service for Nexus Predictor V2.4.

V2.4 extends the evidence layer with a mixed ingestion strategy:

- Editable JSON for curated/candidate platform profiles.
- Editable CSV for fragile social metrics that usually need manual capture.
- Optional Last.fm API refresh for top tracks, used as the clean alternative to
  Spotify top tracks when Spotify returns 403.

The service deliberately stores uncertain rows with low/medium confidence and
clear notes. This keeps the model explainable and avoids treating public or
manual research as absolute truth.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from sqlalchemy import delete, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.paths import BACKEND_DIR, MANUAL_SOCIAL_METRICS_CSV_PATH, SOCIAL_PLATFORM_SEED_PATH
from app.db.models import (
    ArtistMetricModel,
    ArtistModel,
    EvidenceItemModel,
    PlatformProfileModel,
    SocialProfileModel,
    SourceModel,
)
from app.services.database_seed_service import dumps_json, seed_database_from_json
from app.services.evidence_seed_service import create_evidence, get_or_create_source, normalize_confidence, upsert_artist_metric
from app.services.external_http_service import ExternalServiceError

# Load backend/.env for CLI scripts. FastAPI already loads settings elsewhere,
# but direct scripts benefit from this explicit local load.
load_dotenv(BACKEND_DIR / ".env")

SOCIAL_PLATFORMS = {"instagram", "tiktok", "youtube", "facebook", "x_twitter"}
MUSIC_PLATFORMS = {"lastfm", "soundcloud", "apple_music", "beatport", "1001tracklists", "youtube"}
SOCIAL_METRIC_PREFIXES = (
    "social.",
    "platform.",
    "lastfm.",
)
V2_4_SOURCE_KEYS = {
    "v2_social_manual_profiles",
    "v2_music_platform_manual_profiles",
    "lastfm_api",
    "v2_social_manual_csv",
}


@dataclass(slots=True)
class LastfmStatus:
    """Small status object for the optional Last.fm API integration."""

    configured: bool
    api_base_url: str
    top_track_limit: int
    message: str


class SocialPlatformService:
    """Persist V2.4 social and music-platform signals into the evidence layer."""

    def __init__(
        self,
        db: Session,
        *,
        seed_path: Path = SOCIAL_PLATFORM_SEED_PATH,
        csv_path: Path = MANUAL_SOCIAL_METRICS_CSV_PATH,
    ) -> None:
        """Store the request-scoped database session and input paths."""
        self.db = db
        self.seed_path = seed_path
        self.csv_path = csv_path
        self.lastfm_api_key = os.getenv("LASTFM_API_KEY", "").strip()
        self.lastfm_api_base_url = os.getenv("LASTFM_API_BASE_URL", "https://ws.audioscrobbler.com/2.0/").strip()
        self.lastfm_top_track_limit = int(os.getenv("LASTFM_TOP_TRACK_LIMIT", "10") or "10")
        self.lastfm_user_agent = os.getenv(
            "LASTFM_USER_AGENT",
            "NexusPredictor/2.4 (local research app; http://127.0.0.1:8000)",
        ).strip()
        self.timeout_seconds = float(os.getenv("EXTERNAL_REQUEST_TIMEOUT_SECONDS", "20") or "20")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Return safe public status for Last.fm and manual ingestion."""
        status = LastfmStatus(
            configured=bool(self.lastfm_api_key),
            api_base_url=self.lastfm_api_base_url,
            top_track_limit=self.lastfm_top_track_limit,
            message=(
                "Last.fm API key is configured."
                if self.lastfm_api_key
                else "Last.fm API key is not configured; manual/JSON social ingestion still works."
            ),
        )
        return {
            "lastfm": asdict(status),
            "manual_json_seed_exists": self.seed_path.exists(),
            "manual_csv_seed_exists": self.csv_path.exists(),
            "supported_social_platforms": sorted(SOCIAL_PLATFORMS),
            "supported_music_platforms": sorted(MUSIC_PLATFORMS),
        }

    def run(self, *, reset: bool = False, limit_artists: int | None = None) -> dict[str, Any]:
        """Run the V2.4 mixed ingestion from JSON and CSV seeds."""
        seed_database_from_json(self.db, reset=False)

        if reset:
            self.reset_v2_4_rows()

        seed = self.load_seed()
        sources = self.ensure_sources(seed)
        summary = {
            "sources": len(sources),
            "social_profiles": 0,
            "platform_profiles": 0,
            "evidence_items": 0,
            "artist_metrics": 0,
            "artists_processed": 0,
            "manual_csv_rows": 0,
            "warnings": [],
        }

        artists = list(seed.get("artists", []))
        if limit_artists is not None:
            artists = artists[:limit_artists]

        for artist_payload in artists:
            result = self.ingest_artist_payload(artist_payload, sources)
            summary["social_profiles"] += result["social_profiles"]
            summary["platform_profiles"] += result["platform_profiles"]
            summary["evidence_items"] += result["evidence_items"]
            summary["artist_metrics"] += result["artist_metrics"]
            summary["artists_processed"] += result["artists_processed"]
            summary["warnings"].extend(result["warnings"])

        csv_result = self.import_manual_csv()
        summary["manual_csv_rows"] = csv_result["rows"]
        summary["social_profiles"] += csv_result["social_profiles"]
        summary["evidence_items"] += csv_result["evidence_items"]
        summary["artist_metrics"] += csv_result["artist_metrics"]
        summary["warnings"].extend(csv_result["warnings"])

        # Recalculate scores for all artists touched by JSON or CSV ingestion.
        touched_slugs = sorted({str(row.get("artist_slug")) for row in artists if row.get("artist_slug")} | set(csv_result["artist_slugs"]))
        for artist_slug in touched_slugs:
            artist = self.get_artist(artist_slug)
            if artist is not None:
                summary["artist_metrics"] += self.recalculate_scores(artist)

        self.db.commit()
        summary["warnings"] = sorted(set(summary["warnings"]))
        return summary

    def coverage(self) -> dict[str, Any]:
        """Return coverage/freshness counts for social and music-platform signals."""
        metric_filters = [ArtistMetricModel.metric_key.startswith(prefix) for prefix in SOCIAL_METRIC_PREFIXES]
        evidence_filters = [EvidenceItemModel.metric_key.startswith(prefix) for prefix in SOCIAL_METRIC_PREFIXES]
        source_filters = [SourceModel.key == key for key in V2_4_SOURCE_KEYS]

        latest_social = self.db.scalar(
            select(func.max(EvidenceItemModel.captured_at)).where(or_(*evidence_filters))
        )
        artists_with_social_profiles = int(
            self.db.scalar(select(func.count(distinct(SocialProfileModel.artist_slug)))) or 0
        )
        artists_with_platform_profiles = int(
            self.db.scalar(select(func.count(distinct(PlatformProfileModel.artist_slug))).where(
                PlatformProfileModel.platform.in_(sorted(MUSIC_PLATFORMS))
            )) or 0
        )
        artists_with_scores = int(
            self.db.scalar(
                select(func.count(distinct(ArtistMetricModel.artist_slug))).where(
                    ArtistMetricModel.metric_key.in_(
                        ["social.reach_score", "social.engagement_score", "social.momentum_score"]
                    )
                )
            )
            or 0
        )
        return {
            "sources": int(self.db.scalar(select(func.count()).select_from(SourceModel).where(or_(*source_filters))) or 0),
            "social_profiles": int(self.db.scalar(select(func.count()).select_from(SocialProfileModel)) or 0),
            "platform_profiles": int(
                self.db.scalar(
                    select(func.count()).select_from(PlatformProfileModel).where(
                        PlatformProfileModel.platform.in_(sorted(MUSIC_PLATFORMS))
                    )
                )
                or 0
            ),
            "social_evidence_items": int(
                self.db.scalar(select(func.count()).select_from(EvidenceItemModel).where(or_(*evidence_filters))) or 0
            ),
            "social_artist_metrics": int(
                self.db.scalar(select(func.count()).select_from(ArtistMetricModel).where(or_(*metric_filters))) or 0
            ),
            "artists_with_social_profiles": artists_with_social_profiles,
            "artists_with_platform_profiles": artists_with_platform_profiles,
            "artists_with_scores": artists_with_scores,
            "lastfm_configured": bool(self.lastfm_api_key),
            "latest_social_capture_at": latest_social,
        }

    def artist_overview(self, artist_slug: str) -> dict[str, Any] | None:
        """Return V2.4 social/platform data for one artist."""
        artist = self.get_artist(artist_slug)
        if artist is None:
            return None

        metric_filters = [ArtistMetricModel.metric_key.startswith(prefix) for prefix in SOCIAL_METRIC_PREFIXES]
        evidence_filters = [EvidenceItemModel.metric_key.startswith(prefix) for prefix in SOCIAL_METRIC_PREFIXES]

        metrics = list(
            self.db.scalars(
                select(ArtistMetricModel)
                .where(ArtistMetricModel.artist_slug == artist.slug)
                .where(or_(*metric_filters))
                .order_by(ArtistMetricModel.metric_key.asc())
            )
        )
        evidence = list(
            self.db.scalars(
                select(EvidenceItemModel)
                .where(EvidenceItemModel.artist_slug == artist.slug)
                .where(or_(*evidence_filters))
                .order_by(EvidenceItemModel.captured_at.desc(), EvidenceItemModel.id.desc())
            )
        )
        social_profiles = list(
            self.db.scalars(
                select(SocialProfileModel)
                .where(SocialProfileModel.artist_slug == artist.slug)
                .order_by(SocialProfileModel.platform.asc())
            )
        )
        platform_profiles = list(
            self.db.scalars(
                select(PlatformProfileModel)
                .where(PlatformProfileModel.artist_slug == artist.slug)
                .where(PlatformProfileModel.platform.in_(sorted(MUSIC_PLATFORMS)))
                .order_by(PlatformProfileModel.platform.asc())
            )
        )
        return {
            "artist_slug": artist.slug,
            "artist_name": artist.name,
            "social_profiles": social_profiles,
            "platform_profiles": platform_profiles,
            "metrics": metrics,
            "evidence_items": evidence,
        }

    def refresh_lastfm_artist(self, artist_slug: str, *, force: bool = False) -> dict[str, Any]:
        """Refresh top tracks for one artist from Last.fm when configured."""
        artist = self.get_artist(artist_slug)
        if artist is None:
            return {
                "artist_slug": artist_slug,
                "configured": bool(self.lastfm_api_key),
                "refreshed": False,
                "message": f"Artist {artist_slug} was not found.",
                "top_tracks": [],
                "warnings": [],
            }

        if not self.lastfm_api_key:
            return {
                "artist_slug": artist.slug,
                "configured": False,
                "refreshed": False,
                "message": "Last.fm API key is missing.",
                "top_tracks": [],
                "warnings": [],
            }

        existing_metric = self.db.scalar(
            select(ArtistMetricModel).where(
                ArtistMetricModel.artist_slug == artist.slug,
                ArtistMetricModel.metric_key == "lastfm.top_track_count",
            )
        )
        if existing_metric is not None and not force:
            return {
                "artist_slug": artist.slug,
                "configured": True,
                "refreshed": False,
                "message": "Last.fm top tracks are already cached. Use force=true to refresh.",
                "top_tracks": [],
                "warnings": [],
            }

        try:
            payload = self.fetch_lastfm_top_tracks(artist.name)
        except ExternalServiceError as exc:
            return {
                "artist_slug": artist.slug,
                "configured": True,
                "refreshed": False,
                "message": "Last.fm refresh failed in a controlled way.",
                "top_tracks": [],
                # Never expose query strings because Last.fm uses api_key in URL params.
                "warnings": [self.redact_sensitive_text(str(exc))],
            }

        tracks = self.normalize_lastfm_tracks(payload)
        source = self.ensure_lastfm_source()
        evidence = create_evidence(
            self.db,
            artist=artist,
            source=source,
            metric_key="lastfm.top_tracks",
            metric_value=tracks,
            value_type="json",
            confidence="high",
            extraction_method="api",
            evidence_kind="music_platform_profile",
            status="official",
            notes="Last.fm top-tracks snapshot used as the V2.4 alternative to Spotify top tracks.",
            source_url=f"https://www.last.fm/music/{artist.name.replace(' ', '+')}",
            raw={"payload_keys": list(payload.keys())},
        )
        self.upsert_platform_profile(
            artist,
            {
                "platform": "lastfm",
                "profile_name": artist.name,
                "profile_url": f"https://www.last.fm/music/{artist.name.replace(' ', '+')}",
                "external_id": None,
                "is_official": True,
                "confidence": "high",
                "notes": "Last.fm profile confirmed through API refresh.",
            },
            evidence.id,
        )
        upsert_artist_metric(
            self.db,
            artist=artist,
            metric_key="lastfm.top_track_count",
            numeric_value=float(len(tracks)),
            value_type="number",
            confidence="high",
            evidence_count=1,
            notes="Number of Last.fm top tracks cached for the artist.",
            raw={"tracks": tracks},
        )
        self.recalculate_scores(artist)
        self.db.commit()
        return {
            "artist_slug": artist.slug,
            "configured": True,
            "refreshed": True,
            "message": "Last.fm top tracks refreshed successfully.",
            "top_tracks": tracks,
            "warnings": [],
        }

    # ------------------------------------------------------------------
    # Seed loading and source registry
    # ------------------------------------------------------------------
    def load_seed(self) -> dict[str, Any]:
        """Load the editable JSON social/platform seed."""
        if not self.seed_path.exists():
            raise RuntimeError(f"Missing V2.4 social-platform seed: {self.seed_path}")
        return json.loads(self.seed_path.read_text(encoding="utf-8"))

    def ensure_sources(self, seed: dict[str, Any]) -> dict[str, SourceModel]:
        """Create/update V2.4 source registry rows."""
        sources: dict[str, SourceModel] = {}
        for source in seed.get("sources", []):
            created = get_or_create_source(
                self.db,
                key=source["key"],
                name=source["name"],
                source_type=source["source_type"],
                base_url=source.get("base_url"),
                confidence=source.get("confidence", "medium"),
                extraction_method=source.get("extraction_method", "manual_seed"),
                notes=source.get("notes"),
                raw=source,
            )
            sources[created.key] = created

        csv_source = get_or_create_source(
            self.db,
            key="v2_social_manual_csv",
            name="Manual social metrics CSV V2.4",
            source_type="social_manual",
            base_url=None,
            confidence="medium",
            extraction_method="csv_manual",
            notes="Editable CSV import for fragile social counters and manual research rows.",
            raw={"path": str(self.csv_path)},
        )
        sources[csv_source.key] = csv_source
        self.db.flush()
        return sources

    def ensure_lastfm_source(self) -> SourceModel:
        """Get/create the Last.fm API source row."""
        return get_or_create_source(
            self.db,
            key="lastfm_api",
            name="Last.fm API",
            source_type="music_platform",
            base_url="https://www.last.fm/",
            confidence="high",
            extraction_method="api",
            notes="Optional API source used in V2.4 to retrieve top tracks.",
            raw={"api_base_url": self.lastfm_api_base_url},
        )

    # ------------------------------------------------------------------
    # Import implementations
    # ------------------------------------------------------------------
    def ingest_artist_payload(self, artist_payload: dict[str, Any], sources: dict[str, SourceModel]) -> dict[str, Any]:
        """Persist one artist payload from the JSON seed."""
        result = {
            "social_profiles": 0,
            "platform_profiles": 0,
            "evidence_items": 0,
            "artist_metrics": 0,
            "artists_processed": 0,
            "warnings": [],
        }
        artist_slug = str(artist_payload.get("artist_slug", "")).strip()
        artist = self.get_artist(artist_slug)
        if artist is None:
            result["warnings"].append(f"Unknown artist in V2.4 seed: {artist_slug}")
            return result

        social_source = sources["v2_social_manual_profiles"]
        music_source = sources["v2_music_platform_manual_profiles"]
        result["artists_processed"] = 1

        for profile in artist_payload.get("social_profiles", []):
            evidence = self.create_social_profile_evidence(artist, profile, social_source)
            self.upsert_social_profile(artist, profile, evidence.id)
            result["social_profiles"] += 1
            result["evidence_items"] += 1

        for profile in artist_payload.get("platform_profiles", []):
            evidence = self.create_platform_profile_evidence(artist, profile, music_source)
            self.upsert_platform_profile(artist, profile, evidence.id)
            result["platform_profiles"] += 1
            result["evidence_items"] += 1

        return result

    def import_manual_csv(self) -> dict[str, Any]:
        """Import optional manual CSV rows for fragile social metrics."""
        result = {
            "rows": 0,
            "social_profiles": 0,
            "evidence_items": 0,
            "artist_metrics": 0,
            "artist_slugs": [],
            "warnings": [],
        }
        if not self.csv_path.exists():
            result["warnings"].append(f"Manual social CSV not found: {self.csv_path}")
            return result

        source = get_or_create_source(
            self.db,
            key="v2_social_manual_csv",
            name="Manual social metrics CSV V2.4",
            source_type="social_manual",
            base_url=None,
            confidence="medium",
            extraction_method="csv_manual",
            notes="Editable CSV import for social counters and fragile platform metrics.",
            raw={"path": str(self.csv_path)},
        )
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                artist_slug = (row.get("artist_slug") or "").strip()
                artist = self.get_artist(artist_slug)
                if artist is None:
                    result["warnings"].append(f"Unknown artist in manual CSV: {artist_slug}")
                    continue

                profile = {
                    "platform": (row.get("platform") or "").strip(),
                    "profile_url": (row.get("profile_url") or "").strip() or None,
                    "handle": (row.get("handle") or "").strip() or None,
                    "follower_count": self.parse_int(row.get("follower_count")),
                    "engagement_rate": self.parse_float(row.get("engagement_rate")),
                    "average_views": self.parse_int(row.get("average_views")),
                    "last_post_at": (row.get("last_post_at") or "").strip() or None,
                    "is_official": self.parse_bool(row.get("is_official")),
                    "confidence": (row.get("confidence") or "low").strip(),
                    "notes": (row.get("notes") or "").strip() or "Manual social metric imported from CSV.",
                }
                evidence = self.create_social_profile_evidence(artist, profile, source)
                self.upsert_social_profile(artist, profile, evidence.id)
                result["rows"] += 1
                result["social_profiles"] += 1
                result["evidence_items"] += 1
                result["artist_slugs"].append(artist.slug)
        return result

    def create_social_profile_evidence(
        self,
        artist: ArtistModel,
        profile: dict[str, Any],
        source: SourceModel,
    ) -> EvidenceItemModel:
        """Create one evidence row for a social profile/counter bundle."""
        platform = self.clean_platform(profile.get("platform"))
        return create_evidence(
            self.db,
            artist=artist,
            source=source,
            metric_key=f"social.{platform}.profile",
            metric_value={
                "platform": platform,
                "handle": profile.get("handle"),
                "profile_url": profile.get("profile_url"),
                "follower_count": profile.get("follower_count"),
                "engagement_rate": profile.get("engagement_rate"),
                "average_views": profile.get("average_views"),
                "last_post_at": profile.get("last_post_at"),
                "is_official": bool(profile.get("is_official")),
            },
            value_type="json",
            confidence=profile.get("confidence", "medium"),
            extraction_method=source.extraction_method,
            evidence_kind="social_profile",
            status="confirmed" if profile.get("is_official") else "pending_review",
            notes=profile.get("notes"),
            source_url=profile.get("profile_url"),
            raw=profile,
        )

    def create_platform_profile_evidence(
        self,
        artist: ArtistModel,
        profile: dict[str, Any],
        source: SourceModel,
    ) -> EvidenceItemModel:
        """Create one evidence row for a music-platform profile."""
        platform = self.clean_platform(profile.get("platform"))
        return create_evidence(
            self.db,
            artist=artist,
            source=source,
            metric_key=f"platform.{platform}.profile_url",
            metric_value={
                "platform": platform,
                "profile_name": profile.get("profile_name"),
                "profile_url": profile.get("profile_url"),
                "external_id": profile.get("external_id"),
                "is_official": bool(profile.get("is_official")),
            },
            value_type="json",
            confidence=profile.get("confidence", "medium"),
            extraction_method=source.extraction_method,
            evidence_kind="music_platform_profile",
            status="confirmed" if profile.get("is_official") else "pending_review",
            notes=profile.get("notes"),
            source_url=profile.get("profile_url"),
            raw=profile,
        )

    # ------------------------------------------------------------------
    # Upserts and score calculation
    # ------------------------------------------------------------------
    def upsert_social_profile(self, artist: ArtistModel, profile: dict[str, Any], evidence_id: int | None) -> SocialProfileModel:
        """Insert/update one social profile without duplicating rows."""
        platform = self.clean_platform(profile.get("platform"))
        profile_url = profile.get("profile_url")
        existing = self.db.scalar(
            select(SocialProfileModel).where(
                SocialProfileModel.artist_slug == artist.slug,
                SocialProfileModel.platform == platform,
                SocialProfileModel.profile_url == profile_url,
            )
        )
        model = existing or SocialProfileModel(artist_id=artist.id, artist_slug=artist.slug, platform=platform)
        model.handle = profile.get("handle")
        model.profile_url = profile_url
        model.follower_count = self.parse_int(profile.get("follower_count"))
        model.engagement_rate = self.parse_float(profile.get("engagement_rate"))
        model.average_views = self.parse_int(profile.get("average_views"))
        model.last_post_at = self.parse_datetime(profile.get("last_post_at"))
        model.is_official = bool(profile.get("is_official"))
        model.confidence = normalize_confidence(profile.get("confidence", "medium"))
        model.evidence_id = evidence_id
        model.raw_json = dumps_json(profile)
        if existing is None:
            self.db.add(model)
            self.db.flush()
        return model

    def upsert_platform_profile(
        self,
        artist: ArtistModel,
        profile: dict[str, Any],
        evidence_id: int | None,
    ) -> PlatformProfileModel:
        """Insert/update one music-platform profile without duplicating rows."""
        platform = self.clean_platform(profile.get("platform"))
        profile_url = profile.get("profile_url")
        existing = self.db.scalar(
            select(PlatformProfileModel).where(
                PlatformProfileModel.artist_slug == artist.slug,
                PlatformProfileModel.platform == platform,
                PlatformProfileModel.profile_url == profile_url,
            )
        )
        model = existing or PlatformProfileModel(artist_id=artist.id, artist_slug=artist.slug, platform=platform)
        model.profile_name = profile.get("profile_name")
        model.profile_url = profile_url
        model.external_id = profile.get("external_id")
        model.is_official = bool(profile.get("is_official"))
        model.confidence = normalize_confidence(profile.get("confidence", "medium"))
        model.evidence_id = evidence_id
        model.raw_json = dumps_json(profile)
        if existing is None:
            self.db.add(model)
            self.db.flush()
        return model

    def recalculate_scores(self, artist: ArtistModel) -> int:
        """Calculate V2.4 reach, engagement and momentum scores for one artist."""
        profiles = list(
            self.db.scalars(select(SocialProfileModel).where(SocialProfileModel.artist_slug == artist.slug))
        )
        platform_count = int(
            self.db.scalar(
                select(func.count()).select_from(PlatformProfileModel).where(
                    PlatformProfileModel.artist_slug == artist.slug,
                    PlatformProfileModel.platform.in_(sorted(MUSIC_PLATFORMS)),
                )
            )
            or 0
        )
        total_followers = sum(profile.follower_count or 0 for profile in profiles)
        avg_engagement = self.mean([profile.engagement_rate for profile in profiles if profile.engagement_rate is not None])
        avg_views = self.mean([float(profile.average_views or 0) for profile in profiles if profile.average_views is not None])

        reach_score = self.log_score(total_followers, max_reference=1_500_000)
        engagement_score = min(100.0, (avg_engagement or 0.0) * 18.0)
        views_score = self.log_score(avg_views or 0.0, max_reference=250_000)
        freshness_score = self.freshness_score(profiles)
        momentum_score = round((engagement_score * 0.45) + (views_score * 0.35) + (freshness_score * 0.20), 2)
        music_presence_score = min(100.0, platform_count * 14.0)

        metrics = [
            ("social.total_followers", float(total_followers), "Total followers across imported social profiles."),
            ("social.platform_count", float(len(profiles)), "Number of imported social profiles."),
            ("social.reach_score", reach_score, "Log-scaled social reach score from imported follower counts."),
            ("social.engagement_score", round(engagement_score, 2), "Engagement score derived from imported engagement rates."),
            ("social.momentum_score", momentum_score, "Momentum score combining engagement, average views and recent activity."),
            ("platform.music_presence_score", round(music_presence_score, 2), "Presence score across imported music-platform profiles."),
        ]
        for metric_key, value, notes in metrics:
            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key=metric_key,
                numeric_value=value,
                value_type="number",
                confidence="medium" if value > 0 else "low",
                evidence_count=max(1, len(profiles)),
                notes=notes,
                raw={
                    "total_followers": total_followers,
                    "average_engagement": avg_engagement,
                    "average_views": avg_views,
                    "freshness_score": freshness_score,
                    "platform_count": platform_count,
                },
            )
        return len(metrics)

    # ------------------------------------------------------------------
    # Last.fm HTTP client
    # ------------------------------------------------------------------
    def fetch_lastfm_top_tracks(self, artist_name: str) -> dict[str, Any]:
        """Call Last.fm artist.getTopTracks using the configured API key.

        Last.fm public methods put the API key in the query string. Because
        httpx includes the requested URL in HTTP errors, this method converts
        failed responses into sanitized messages before they reach scripts or
        API responses.
        """
        params = {
            "method": "artist.getTopTracks",
            "artist": artist_name,
            "api_key": self.lastfm_api_key,
            "format": "json",
            "limit": self.lastfm_top_track_limit,
            "autocorrect": 1,
        }
        headers = {"User-Agent": self.lastfm_user_agent}

        try:
            with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
                response = client.get(self.lastfm_api_base_url, params=params)

                # Some edge/WAF setups are stricter with anonymous-looking GET
                # requests. A POST retry is safe for Last.fm webservice methods
                # and keeps the refresh useful without adding a hacky scraper.
                if response.status_code == 403:
                    post_response = client.post(self.lastfm_api_base_url, data=params)
                    if post_response.status_code != 403:
                        response = post_response

                if response.is_error:
                    raise ExternalServiceError(self.build_lastfm_error_message(response))

                payload = response.json()
        except httpx.RequestError as exc:
            raise ExternalServiceError(
                f"Last.fm request failed before receiving a response: {self.redact_sensitive_text(str(exc))}"
            ) from exc
        except ValueError as exc:
            raise ExternalServiceError("Last.fm returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ExternalServiceError("Last.fm returned an unexpected payload.")
        if "error" in payload:
            raise ExternalServiceError(
                f"Last.fm error {payload.get('error')}: {payload.get('message', 'Unknown error.')}"
            )
        return payload

    def build_lastfm_error_message(self, response: httpx.Response) -> str:
        """Create a useful Last.fm HTTP error without leaking the API key."""
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict) and "error" in payload:
            return f"Last.fm error {payload.get('error')}: {payload.get('message', 'Unknown error.')}"

        reason = response.reason_phrase or "Unknown error"
        message = f"Last.fm request failed with HTTP {response.status_code} {reason}."
        if response.status_code == 403:
            message += (
                " The key may be inactive/revoked, the account may not be allowed yet, "
                "the IP may be blocked, or Last.fm may be denying the request temporarily."
            )
        return message

    @staticmethod
    def redact_sensitive_text(value: str) -> str:
        """Remove API keys from exception strings before returning warnings."""
        return re.sub(r"(api_key=)[^&'\"\s]+", r"\1<redacted>", value)

    def normalize_lastfm_tracks(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize Last.fm top-track payload into a compact, stable list."""
        raw_tracks = payload.get("toptracks", {}).get("track", [])
        if isinstance(raw_tracks, dict):
            raw_tracks = [raw_tracks]
        tracks: list[dict[str, Any]] = []
        for index, track in enumerate(raw_tracks, start=1):
            if not isinstance(track, dict):
                continue
            tracks.append(
                {
                    "rank": index,
                    "name": track.get("name"),
                    "playcount": self.parse_int(track.get("playcount")),
                    "listeners": self.parse_int(track.get("listeners")),
                    "url": track.get("url"),
                }
            )
        return tracks

    # ------------------------------------------------------------------
    # Reset and helpers
    # ------------------------------------------------------------------
    def reset_v2_4_rows(self) -> None:
        """Delete only V2.4 rows without touching V2.1/V2.2/V2.3 evidence."""
        metric_filters = [ArtistMetricModel.metric_key.startswith(prefix) for prefix in SOCIAL_METRIC_PREFIXES]
        evidence_filters = [EvidenceItemModel.metric_key.startswith(prefix) for prefix in SOCIAL_METRIC_PREFIXES]

        self.db.execute(delete(SocialProfileModel).where(SocialProfileModel.platform.in_(sorted(SOCIAL_PLATFORMS))))
        self.db.execute(delete(PlatformProfileModel).where(PlatformProfileModel.platform.in_(sorted(MUSIC_PLATFORMS))))
        self.db.execute(delete(ArtistMetricModel).where(or_(*metric_filters)))
        self.db.execute(delete(EvidenceItemModel).where(or_(*evidence_filters)))
        self.db.flush()

    def get_artist(self, artist_slug: str) -> ArtistModel | None:
        """Return an artist by slug."""
        if not artist_slug:
            return None
        return self.db.scalar(select(ArtistModel).where(ArtistModel.slug == artist_slug))

    @staticmethod
    def clean_platform(platform: Any) -> str:
        """Normalize platform identifiers for stable metric keys."""
        return str(platform or "unknown").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def parse_int(value: Any) -> int | None:
        """Parse an optional integer from CSV/JSON values."""
        if value is None or value == "":
            return None
        try:
            return int(float(str(value).replace(",", "").strip()))
        except ValueError:
            return None

    @staticmethod
    def parse_float(value: Any) -> float | None:
        """Parse an optional float from CSV/JSON values."""
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", ".").strip())
        except ValueError:
            return None

    @staticmethod
    def parse_bool(value: Any) -> bool:
        """Parse bool-like CSV/JSON values."""
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "y", "si", "sí"}

    @staticmethod
    def parse_datetime(value: Any) -> datetime | None:
        """Parse ISO datetimes used by manual seeds."""
        if value is None or value == "":
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    @staticmethod
    def mean(values: list[float]) -> float | None:
        """Return the arithmetic mean or None for empty lists."""
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def log_score(value: float, *, max_reference: float) -> float:
        """Return a stable 0-100 logarithmic score for large counters."""
        if value <= 0:
            return 0.0
        score = math.log10(value + 1) / math.log10(max_reference + 1) * 100.0
        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def freshness_score(profiles: list[SocialProfileModel]) -> float:
        """Score recent activity from last_post_at when available."""
        dated_profiles = [profile for profile in profiles if profile.last_post_at is not None]
        if not dated_profiles:
            return 0.0
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        best = 0.0
        for profile in dated_profiles:
            days = max(0, (now - profile.last_post_at).days)
            if days <= 30:
                candidate = 100.0
            elif days <= 90:
                candidate = 70.0
            elif days <= 180:
                candidate = 45.0
            else:
                candidate = 20.0
            best = max(best, candidate)
        return best
