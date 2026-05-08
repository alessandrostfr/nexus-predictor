"""Service layer for V3.3 artist identity resolution.

This block is deliberately not a scraper and not a model trainer. Its job is to
make sure external platform data can only become ML features after it has been
attached to the correct canonical artist with enough confidence.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    ArtistAliasModel,
    ArtistIdentityCandidateModel,
    ArtistIdentityLinkModel,
    ArtistMasterModel,
    ArtistModel,
    PlatformProfileModel,
    SocialProfileModel,
    SpotifyArtistCacheModel,
)
from app.schemas.identity import (
    ArtistAliasRecord,
    ArtistIdentityCandidateListResponse,
    ArtistIdentityCandidateRecord,
    ArtistIdentityLinkRecord,
    ArtistMasterDetail,
    ArtistMasterListResponse,
    ArtistMasterSummary,
    IdentityConvention,
    IdentityConventionsResponse,
    IdentityCoverageResponse,
    IdentityRebuildResult,
    ReviewIdentityCandidateRequest,
    ReviewIdentityCandidateResult,
)

FEATURE_ELIGIBLE_CONFIDENCE = {"verified", "high"}
CONFIDENCE_ORDER = {"verified": 1.0, "high": 0.85, "medium": 0.65, "low": 0.35, "rejected": 0.0, "unknown": 0.1}
TOP_ARTIST_MIN_APPEARANCES = 3


def loads_json(value: str | None, fallback: Any) -> Any:
    """Deserialize Text JSON used by legacy V1/V2 tables safely."""
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def normalize_artist_name(value: str | None) -> str:
    """Normalize a name for deterministic artist matching.

    This is not ML. It is a transparent rule-based normalizer used before human
    review and later entity-resolution features. It removes accents, lowers case,
    removes punctuation, and strips collaboration separators.
    """
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = ascii_value.replace("&", " and ")
    ascii_value = re.sub(r"\b(b2b|vs|versus|pres|presents|feat|ft|and)\b", " ", ascii_value)
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return re.sub(r"\s+", " ", ascii_value).strip()


def split_performance_aliases(value: str | None) -> list[str]:
    """Extract useful aliases from a performance display name.

    Examples such as `Adrenalize vs Atmozfears` are kept as a full show alias and
    split into artist-name candidates. This helps V3.3 catch ambiguous or b2b
    cases before external metrics are consumed.
    """
    if not value:
        return []
    parts = [value]
    splitters = r"\b(?:b2b|vs|versus|and|pres\.|presents|feat\.|ft\.)\b|&|/|\+"
    for part in re.split(splitters, value, flags=re.IGNORECASE):
        cleaned = part.strip(" -–—:,()[]")
        if cleaned and len(cleaned) >= 2:
            parts.append(cleaned)
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        key = normalize_artist_name(part)
        if key and key not in seen:
            seen.add(key)
            result.append(part.strip())
    return result


def match_score(name_a: str | None, name_b: str | None) -> float:
    """Return a deterministic similarity score between two display names."""
    left = normalize_artist_name(name_a)
    right = normalize_artist_name(name_b)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return round(SequenceMatcher(None, left, right).ratio(), 4)


def status_from_confidence(confidence: str, *, is_official: bool = False) -> str:
    """Map a confidence value to a review status."""
    if confidence in FEATURE_ELIGIBLE_CONFIDENCE and is_official:
        return "verified"
    if confidence == "rejected":
        return "rejected"
    return "pending_review"


def is_feature_eligible(confidence: str, status: str) -> bool:
    """Return whether a link is allowed to feed future ML features."""
    return status == "verified" and confidence in FEATURE_ELIGIBLE_CONFIDENCE


class ArtistIdentityResolutionService:
    """Build and inspect the V3.3 identity-resolution layer."""

    def __init__(self, db: Session) -> None:
        self.db = db
        # These in-memory guards make a single rebuild transaction deterministic.
        # Several V2 tables can point to the same external profile URL/id.
        # PostgreSQL would reject that at commit time, so we deduplicate before
        # adding ORM objects to the session.
        self._seen_link_url_keys: set[tuple[int, str, str]] = set()
        self._seen_link_external_keys: set[tuple[int, str, str]] = set()
        self._seen_link_source_keys: set[tuple[int, str, str, int]] = set()
        self._seen_candidate_keys: set[str] = set()

    def _reset_deduplication_guards(self) -> None:
        """Reset in-memory dedupe guards for each rebuild call.

        The API can call rebuild many times in the same Python process during
        tests or local validation. The guards must therefore be local to one
        rebuild execution, not permanent process state.
        """
        self._seen_link_url_keys.clear()
        self._seen_link_external_keys.clear()
        self._seen_link_source_keys.clear()
        self._seen_candidate_keys.clear()

    @staticmethod
    def _clean_identity_value(value: str | None) -> str | None:
        """Normalize URLs/external ids enough to deduplicate exact profiles."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned.lower() if cleaned else None

    def _add_identity_link(self, link: ArtistIdentityLinkModel) -> ArtistIdentityLinkModel | None:
        """Add an identity link only if it is unique for the canonical artist.

        V2 can store the same Spotify/Social URL in more than one source table
        or with repeated rows. V3.3 wants one canonical link per
        artist/platform/profile, so duplicate source rows are treated as
        supporting evidence, not as separate feature-eligible links.
        """
        platform = (link.platform or "unknown").strip().lower()
        profile_url = self._clean_identity_value(link.profile_url)
        external_id = self._clean_identity_value(link.external_id)

        url_key = (link.artist_master_id, platform, profile_url) if profile_url else None
        external_key = (link.artist_master_id, platform, external_id) if external_id else None
        source_key = (
            (link.artist_master_id, platform, link.source_table, int(link.source_record_id))
            if link.source_table and link.source_record_id is not None
            else None
        )

        if url_key is not None and url_key in self._seen_link_url_keys:
            return None
        if external_key is not None and external_key in self._seen_link_external_keys:
            return None
        if source_key is not None and source_key in self._seen_link_source_keys:
            return None

        # reset=false should also be safe: skip rows already committed in DB.
        with self.db.no_autoflush:
            if url_key is not None:
                existing_by_url = self.db.scalar(
                    select(ArtistIdentityLinkModel.id).where(
                        ArtistIdentityLinkModel.artist_master_id == link.artist_master_id,
                        ArtistIdentityLinkModel.platform == link.platform,
                        ArtistIdentityLinkModel.profile_url == link.profile_url,
                    )
                )
                if existing_by_url is not None:
                    return None
            if external_key is not None:
                existing_by_external_id = self.db.scalar(
                    select(ArtistIdentityLinkModel.id).where(
                        ArtistIdentityLinkModel.artist_master_id == link.artist_master_id,
                        ArtistIdentityLinkModel.platform == link.platform,
                        ArtistIdentityLinkModel.external_id == link.external_id,
                    )
                )
                if existing_by_external_id is not None:
                    return None

        self.db.add(link)
        if url_key is not None:
            self._seen_link_url_keys.add(url_key)
        if external_key is not None:
            self._seen_link_external_keys.add(external_key)
        if source_key is not None:
            self._seen_link_source_keys.add(source_key)
        return link

    def rebuild(self, *, reset: bool = True) -> IdentityRebuildResult:
        """Rebuild canonical artist identities from the current V1/V2 seed data."""
        self._reset_deduplication_guards()
        if reset:
            self.db.execute(delete(ArtistIdentityCandidateModel))
            self.db.execute(delete(ArtistIdentityLinkModel))
            self.db.execute(delete(ArtistAliasModel))
            self.db.execute(delete(ArtistMasterModel))
            self.db.flush()

        artists = list(self.db.scalars(select(ArtistModel).order_by(ArtistModel.slug)))
        master_by_slug: dict[str, ArtistMasterModel] = {}
        aliases_created = 0
        links_created = 0
        candidates_created = 0

        for artist in artists:
            appearance_years = loads_json(artist.appearance_years_json, [])
            appearances = loads_json(artist.appearances_json, [])
            is_2026_artist = 2026 in {int(year) for year in appearance_years if str(year).isdigit()}
            is_top_artist = artist.appearance_count >= TOP_ARTIST_MIN_APPEARANCES or is_2026_artist
            needs_review = bool(artist.manual_review or is_top_artist)
            master = ArtistMasterModel(
                artist_id=artist.id,
                canonical_artist_key=artist.slug,
                source_artist_slug=artist.slug,
                display_name=artist.name,
                normalized_name=normalize_artist_name(artist.name),
                primary_genre_seed=artist.primary_genre_seed,
                appearance_count=artist.appearance_count,
                is_2026_artist=is_2026_artist,
                is_top_artist=is_top_artist,
                needs_manual_review=needs_review,
                review_status="needs_external_review" if needs_review else "seed_verified",
                feature_eligibility_status="internal_seed_only",
                alias_payload={"source": "artists", "appearance_aliases": appearances},
                appearances_payload={"appearance_years": appearance_years, "appearances": appearances},
                raw_payload=loads_json(artist.raw_json, {}),
                notes="Seeded from the canonical V1/V2 artists table. External profiles still require V3.3 confidence gates.",
            )
            self.db.add(master)
            self.db.flush()
            master_by_slug[artist.slug] = master

            alias_values: list[tuple[str, str, str]] = [
                (artist.name, "display_name", "verified"),
                (artist.normalized_name, "normalized_seed", "high"),
            ]
            for appearance in appearances:
                display = appearance.get("performance_display_name") if isinstance(appearance, dict) else None
                for alias in split_performance_aliases(display):
                    alias_values.append((alias, "performance_alias", "medium"))

            seen_aliases: set[tuple[str, str]] = set()
            for alias, alias_type, confidence in alias_values:
                normalized_alias = normalize_artist_name(alias)
                if not normalized_alias:
                    continue
                key = (normalized_alias, alias_type)
                if key in seen_aliases:
                    continue
                seen_aliases.add(key)
                self.db.add(
                    ArtistAliasModel(
                        artist_master_id=master.id,
                        canonical_artist_key=master.canonical_artist_key,
                        alias=alias,
                        normalized_alias=normalized_alias,
                        alias_type=alias_type,
                        source_key="nexus_seed",
                        confidence=confidence,
                        status="active",
                        raw_payload={"artist_slug": artist.slug, "alias_type": alias_type},
                    )
                )
                aliases_created += 1

            internal_link = self._add_identity_link(
                ArtistIdentityLinkModel(
                    artist_master_id=master.id,
                    artist_id=artist.id,
                    canonical_artist_key=master.canonical_artist_key,
                    platform="nexus_seed",
                    profile_name=artist.name,
                    normalized_profile_name=master.normalized_name,
                    external_id=artist.slug,
                    confidence="verified",
                    confidence_score=1.0,
                    match_status="verified",
                    match_method="internal_artist_seed",
                    source_table="artists",
                    source_record_id=artist.id,
                    is_primary=True,
                    is_feature_eligible=True,
                    requires_manual_review=False,
                    reviewed_at=datetime.utcnow(),
                    reviewed_by="system",
                    review_notes="Internal Nexus seed identity is the canonical starting point.",
                    raw_payload={"source_artist_slug": artist.slug},
                )
            )
            if internal_link is not None:
                links_created += 1

        self.db.flush()
        links_created += self._import_spotify_links(master_by_slug)
        imported_profiles = self._import_platform_profiles(master_by_slug)
        links_created += imported_profiles["links"]
        candidates_created += imported_profiles["candidates"]
        imported_social = self._import_social_profiles(master_by_slug)
        links_created += imported_social["links"]
        candidates_created += imported_social["candidates"]

        self.db.commit()
        coverage = self.coverage()
        return IdentityRebuildResult(
            artists_seen=len(artists),
            masters_created=int(coverage.masters),
            aliases_created=aliases_created,
            links_created=links_created,
            candidates_created=candidates_created,
            top_artists_requiring_review=coverage.top_artists_requiring_review,
            feature_eligible_links=coverage.feature_eligible_links,
            minimum_feature_confidence=sorted(FEATURE_ELIGIBLE_CONFIDENCE),
            top_artist_policy="Top/2026 artists keep needs_manual_review=True for external profiles, even when the internal Nexus seed is verified.",
        )

    def _import_spotify_links(self, master_by_slug: dict[str, ArtistMasterModel]) -> int:
        """Create Spotify identity links/candidates from the existing V2 cache."""
        created = 0
        rows = self.db.scalars(select(SpotifyArtistCacheModel)).all()
        for row in rows:
            master = master_by_slug.get(row.artist_slug)
            if master is None:
                continue
            score = match_score(master.display_name, row.name)
            confidence = row.match_confidence or "medium"
            status = "verified" if confidence in FEATURE_ELIGIBLE_CONFIDENCE and score >= 0.82 else "pending_review"
            feature_ok = is_feature_eligible(confidence, status)
            link = self._add_identity_link(
                ArtistIdentityLinkModel(
                    artist_master_id=master.id,
                    artist_id=row.artist_id,
                    canonical_artist_key=master.canonical_artist_key,
                    platform="spotify",
                    profile_name=row.name,
                    normalized_profile_name=normalize_artist_name(row.name),
                    profile_url=row.spotify_url,
                    external_id=row.spotify_artist_id,
                    confidence=confidence,
                    confidence_score=score,
                    match_status=status,
                    match_method=row.match_method or "spotify_cache_match",
                    source_table="spotify_artist_cache",
                    source_record_id=row.id,
                    is_primary=True,
                    is_feature_eligible=feature_ok,
                    requires_manual_review=not feature_ok,
                    reviewed_at=datetime.utcnow() if feature_ok else None,
                    reviewed_by="system" if feature_ok else None,
                    raw_payload={"spotify_uri": row.spotify_uri, "followers": row.followers, "popularity": row.popularity},
                )
            )
            if link is not None:
                created += 1
            if not feature_ok:
                self._add_candidate(
                    master=master,
                    platform="spotify",
                    candidate_name=row.name,
                    candidate_url=row.spotify_url,
                    external_id=row.spotify_artist_id,
                    match_score=score,
                    confidence=confidence,
                    source_table="spotify_artist_cache",
                    source_record_id=row.id,
                    evidence_payload={"reason": "Spotify cache match needs review before feature usage."},
                )
        return created

    def _import_platform_profiles(self, master_by_slug: dict[str, ArtistMasterModel]) -> dict[str, int]:
        """Import generic V2 platform profile rows as V3 identity links."""
        links = 0
        candidates = 0
        rows = self.db.scalars(select(PlatformProfileModel)).all()
        for row in rows:
            master = master_by_slug.get(row.artist_slug)
            if master is None:
                continue
            profile_name = row.profile_name or master.display_name
            score = match_score(master.display_name, profile_name)
            confidence = row.confidence or "medium"
            status = status_from_confidence(confidence, is_official=row.is_official and score >= 0.82)
            feature_ok = is_feature_eligible(confidence, status)
            link = self._add_identity_link(
                ArtistIdentityLinkModel(
                    artist_master_id=master.id,
                    artist_id=row.artist_id,
                    canonical_artist_key=master.canonical_artist_key,
                    platform=row.platform,
                    profile_name=profile_name,
                    normalized_profile_name=normalize_artist_name(profile_name),
                    profile_url=row.profile_url,
                    external_id=row.external_id,
                    confidence=confidence,
                    confidence_score=score,
                    match_status=status,
                    match_method="platform_profile_seed",
                    source_table="platform_profiles",
                    source_record_id=row.id,
                    is_primary=row.is_official,
                    is_feature_eligible=feature_ok,
                    requires_manual_review=not feature_ok,
                    reviewed_at=datetime.utcnow() if feature_ok else None,
                    reviewed_by="system" if feature_ok else None,
                    raw_payload=loads_json(row.raw_json, {}),
                )
            )
            if link is not None:
                links += 1
            if not feature_ok:
                self._add_candidate(
                    master=master,
                    platform=row.platform,
                    candidate_name=profile_name,
                    candidate_url=row.profile_url,
                    external_id=row.external_id,
                    match_score=score,
                    confidence=confidence,
                    source_table="platform_profiles",
                    source_record_id=row.id,
                    evidence_payload={"is_official": row.is_official, "reason": "Platform profile needs manual review."},
                )
                candidates += 1
        return {"links": links, "candidates": candidates}

    def _import_social_profiles(self, master_by_slug: dict[str, ArtistMasterModel]) -> dict[str, int]:
        """Import V2 social profile rows as V3 identity links."""
        links = 0
        candidates = 0
        rows = self.db.scalars(select(SocialProfileModel)).all()
        for row in rows:
            master = master_by_slug.get(row.artist_slug)
            if master is None:
                continue
            profile_name = row.handle or master.display_name
            score = match_score(master.display_name, profile_name)
            confidence = row.confidence or "medium"
            status = status_from_confidence(confidence, is_official=row.is_official and score >= 0.82)
            feature_ok = is_feature_eligible(confidence, status)
            link = self._add_identity_link(
                ArtistIdentityLinkModel(
                    artist_master_id=master.id,
                    artist_id=row.artist_id,
                    canonical_artist_key=master.canonical_artist_key,
                    platform=row.platform,
                    profile_name=profile_name,
                    normalized_profile_name=normalize_artist_name(profile_name),
                    profile_url=row.profile_url,
                    external_id=row.handle,
                    confidence=confidence,
                    confidence_score=score,
                    match_status=status,
                    match_method="social_profile_seed",
                    source_table="social_profiles",
                    source_record_id=row.id,
                    is_primary=row.is_official,
                    is_feature_eligible=feature_ok,
                    requires_manual_review=not feature_ok,
                    reviewed_at=datetime.utcnow() if feature_ok else None,
                    reviewed_by="system" if feature_ok else None,
                    raw_payload={"followers": row.follower_count, "engagement_rate": row.engagement_rate, "average_views": row.average_views},
                )
            )
            if link is not None:
                links += 1
            if not feature_ok:
                self._add_candidate(
                    master=master,
                    platform=row.platform,
                    candidate_name=profile_name,
                    candidate_url=row.profile_url,
                    external_id=row.handle,
                    match_score=score,
                    confidence=confidence,
                    source_table="social_profiles",
                    source_record_id=row.id,
                    evidence_payload={"is_official": row.is_official, "reason": "Social profile needs manual review."},
                )
                candidates += 1
        return {"links": links, "candidates": candidates}

    def _add_candidate(
        self,
        *,
        master: ArtistMasterModel,
        platform: str,
        candidate_name: str,
        candidate_url: str | None,
        external_id: str | None,
        match_score: float,
        confidence: str,
        source_table: str,
        source_record_id: int,
        evidence_payload: dict[str, object],
    ) -> None:
        """Add a candidate row if it does not already exist in this rebuild."""
        raw_key = external_id or candidate_url or candidate_name
        candidate_key = f"{master.canonical_artist_key}:{platform}:{normalize_artist_name(raw_key)}"
        if candidate_key in self._seen_candidate_keys:
            return
        with self.db.no_autoflush:
            existing = self.db.scalar(select(ArtistIdentityCandidateModel).where(ArtistIdentityCandidateModel.candidate_key == candidate_key))
        if existing is not None:
            return
        self._seen_candidate_keys.add(candidate_key)
        self.db.add(
            ArtistIdentityCandidateModel(
                artist_master_id=master.id,
                artist_id=master.artist_id,
                canonical_artist_key=master.canonical_artist_key,
                candidate_key=candidate_key,
                platform=platform,
                candidate_name=candidate_name,
                normalized_candidate_name=normalize_artist_name(candidate_name),
                candidate_url=candidate_url,
                external_id=external_id,
                match_score=match_score,
                confidence=confidence,
                status="pending_review",
                suggested_action="verify" if match_score >= 0.92 and confidence in {"high", "verified"} else "manual_review",
                match_method="profile_seed_similarity",
                source_table=source_table,
                source_record_id=source_record_id,
                evidence_payload=evidence_payload,
            )
        )

    def coverage(self) -> IdentityCoverageResponse:
        """Return V3.3 coverage and guardrail counters."""
        masters = self._count(ArtistMasterModel)
        aliases = self._count(ArtistAliasModel)
        links = self._count(ArtistIdentityLinkModel)
        candidates = self._count(ArtistIdentityCandidateModel)
        pending_candidates = self._count_where(ArtistIdentityCandidateModel, ArtistIdentityCandidateModel.status == "pending_review")
        rejected_candidates = self._count_where(ArtistIdentityCandidateModel, ArtistIdentityCandidateModel.status == "rejected")
        verified_links = self._count_where(ArtistIdentityLinkModel, ArtistIdentityLinkModel.match_status == "verified")
        feature_eligible_links = self._count_where(ArtistIdentityLinkModel, ArtistIdentityLinkModel.is_feature_eligible.is_(True))
        low_confidence_feature_links = self._count_where(
            ArtistIdentityLinkModel,
            ArtistIdentityLinkModel.is_feature_eligible.is_(True),
            ArtistIdentityLinkModel.confidence.notin_(FEATURE_ELIGIBLE_CONFIDENCE),
        )
        top_artists = self._count_where(ArtistMasterModel, ArtistMasterModel.is_top_artist.is_(True))
        top_artists_requiring_review = self._count_where(
            ArtistMasterModel,
            ArtistMasterModel.is_top_artist.is_(True),
            ArtistMasterModel.needs_manual_review.is_(True),
        )
        warnings: list[str] = []
        if masters == 0:
            warnings.append("Identity layer is empty. Run POST /api/v3/identity/rebuild?reset=true.")
        if pending_candidates > 0:
            warnings.append("Some candidate profiles require admin review before they can feed ML features.")
        if low_confidence_feature_links > 0:
            warnings.append("There are low-confidence links marked as feature eligible. This violates V3.3 policy.")
        return IdentityCoverageResponse(
            ready=masters > 0 and low_confidence_feature_links == 0,
            masters=masters,
            aliases=aliases,
            links=links,
            candidates=candidates,
            pending_candidates=pending_candidates,
            verified_links=verified_links,
            rejected_candidates=rejected_candidates,
            feature_eligible_links=feature_eligible_links,
            low_confidence_feature_links=low_confidence_feature_links,
            top_artists=top_artists,
            top_artists_requiring_review=top_artists_requiring_review,
            minimum_feature_confidence=sorted(FEATURE_ELIGIBLE_CONFIDENCE),
            warnings=warnings,
        )

    def list_artists(self, *, query: str | None = None, needs_review: bool | None = None, limit: int = 100, offset: int = 0) -> ArtistMasterListResponse:
        """Return canonical artists with alias/link/candidate counts."""
        filters = []
        if query:
            pattern = f"%{query.lower()}%"
            filters.append(or_(func.lower(ArtistMasterModel.display_name).like(pattern), func.lower(ArtistMasterModel.canonical_artist_key).like(pattern)))
        if needs_review is not None:
            filters.append(ArtistMasterModel.needs_manual_review.is_(needs_review))
        total_stmt = select(func.count()).select_from(ArtistMasterModel)
        stmt = select(ArtistMasterModel).order_by(ArtistMasterModel.is_top_artist.desc(), ArtistMasterModel.display_name).limit(limit).offset(offset)
        if filters:
            total_stmt = total_stmt.where(*filters)
            stmt = stmt.where(*filters)
        total = int(self.db.scalar(total_stmt) or 0)
        masters = list(self.db.scalars(stmt))
        return ArtistMasterListResponse(total=total, limit=limit, offset=offset, items=[self._master_summary(master) for master in masters])

    def get_artist(self, canonical_artist_key: str) -> ArtistMasterDetail | None:
        """Return a canonical artist with aliases and links."""
        master = self.db.scalar(select(ArtistMasterModel).where(ArtistMasterModel.canonical_artist_key == canonical_artist_key))
        if master is None:
            return None
        summary = self._master_summary(master)
        aliases = self.db.scalars(select(ArtistAliasModel).where(ArtistAliasModel.artist_master_id == master.id).order_by(ArtistAliasModel.alias_type, ArtistAliasModel.alias)).all()
        links = self.db.scalars(select(ArtistIdentityLinkModel).where(ArtistIdentityLinkModel.artist_master_id == master.id).order_by(ArtistIdentityLinkModel.platform, ArtistIdentityLinkModel.match_status)).all()
        return ArtistMasterDetail(
            **summary.model_dump(),
            aliases=[self._alias_record(alias) for alias in aliases],
            links=[self._link_record(link) for link in links],
        )

    def list_candidates(self, *, status: str | None = None, confidence: str | None = None, limit: int = 100, offset: int = 0) -> ArtistIdentityCandidateListResponse:
        """Return identity candidates for admin review."""
        filters = []
        if status:
            filters.append(ArtistIdentityCandidateModel.status == status)
        if confidence:
            filters.append(ArtistIdentityCandidateModel.confidence == confidence)
        total_stmt = select(func.count()).select_from(ArtistIdentityCandidateModel)
        stmt = select(ArtistIdentityCandidateModel).order_by(ArtistIdentityCandidateModel.match_score.desc(), ArtistIdentityCandidateModel.id).limit(limit).offset(offset)
        if filters:
            total_stmt = total_stmt.where(*filters)
            stmt = stmt.where(*filters)
        total = int(self.db.scalar(total_stmt) or 0)
        rows = list(self.db.scalars(stmt))
        return ArtistIdentityCandidateListResponse(total=total, limit=limit, offset=offset, items=[self._candidate_record(row) for row in rows])

    def review_candidate(self, candidate_id: int, payload: ReviewIdentityCandidateRequest) -> ReviewIdentityCandidateResult | None:
        """Verify or reject a candidate profile."""
        candidate = self.db.get(ArtistIdentityCandidateModel, candidate_id)
        if candidate is None:
            return None
        decision = payload.decision.strip().lower()
        if decision not in {"verified", "rejected"}:
            raise ValueError("decision must be either 'verified' or 'rejected'.")
        final_confidence = payload.confidence or ("verified" if decision == "verified" else "rejected")
        now = datetime.utcnow()
        candidate.status = decision
        candidate.confidence = final_confidence
        candidate.reviewed_at = now
        candidate.reviewed_by = payload.reviewed_by
        candidate.review_notes = payload.notes

        created_link: ArtistIdentityLinkModel | None = None
        if decision == "verified":
            feature_ok = is_feature_eligible(final_confidence, "verified")
            created_link = ArtistIdentityLinkModel(
                artist_master_id=candidate.artist_master_id,
                artist_id=candidate.artist_id,
                canonical_artist_key=candidate.canonical_artist_key,
                platform=candidate.platform,
                profile_name=candidate.candidate_name,
                normalized_profile_name=candidate.normalized_candidate_name,
                profile_url=candidate.candidate_url,
                external_id=candidate.external_id,
                confidence=final_confidence,
                confidence_score=candidate.match_score,
                match_status="verified",
                match_method="admin_review",
                source_table=candidate.source_table,
                source_record_id=candidate.source_record_id,
                is_primary=False,
                is_feature_eligible=feature_ok,
                requires_manual_review=False,
                reviewed_at=now,
                reviewed_by=payload.reviewed_by,
                review_notes=payload.notes,
                raw_payload=candidate.evidence_payload,
            )
            created_link = self._add_identity_link(created_link)
            if created_link is not None:
                self.db.flush()
        self.db.commit()
        self.db.refresh(candidate)
        if created_link is not None:
            self.db.refresh(created_link)
        return ReviewIdentityCandidateResult(
            candidate=self._candidate_record(candidate),
            created_link=self._link_record(created_link) if created_link is not None else None,
            feature_eligible=created_link.is_feature_eligible if created_link is not None else False,
            message="Candidate verified and linked." if decision == "verified" else "Candidate rejected.",
        )

    def conventions(self) -> IdentityConventionsResponse:
        """Return V3.3 identity-resolution policies."""
        return IdentityConventionsResponse(
            confidence=IdentityConvention(
                key="confidence",
                allowed_values=["verified", "high", "medium", "low", "rejected", "unknown"],
                description="Only verified/high links can become feature eligible in V3.3.",
            ),
            match_status=IdentityConvention(
                key="match_status",
                allowed_values=["verified", "pending_review", "rejected"],
                description="External profile links stay pending until reviewed or high-confidence official.",
            ),
            candidate_status=IdentityConvention(
                key="candidate_status",
                allowed_values=["pending_review", "verified", "rejected"],
                description="Admin review decisions for candidate profiles.",
            ),
            feature_eligibility=IdentityConvention(
                key="feature_eligibility",
                allowed_values=["eligible", "blocked_pending_review", "blocked_low_confidence", "rejected"],
                description="Future feature builders must ignore low/pending/rejected external profiles.",
            ),
            minimum_feature_confidence=sorted(FEATURE_ELIGIBLE_CONFIDENCE),
            top_artist_policy="Artists with >=3 appearances or in the 2026 lineup require manual review for external profiles before ML features use them.",
        )

    def _count(self, model: type) -> int:
        return int(self.db.scalar(select(func.count()).select_from(model)) or 0)

    def _count_where(self, model: type, *conditions: object) -> int:
        return int(self.db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)

    def _master_summary(self, master: ArtistMasterModel) -> ArtistMasterSummary:
        alias_count = self._count_where(ArtistAliasModel, ArtistAliasModel.artist_master_id == master.id)
        link_count = self._count_where(ArtistIdentityLinkModel, ArtistIdentityLinkModel.artist_master_id == master.id)
        candidate_count = self._count_where(ArtistIdentityCandidateModel, ArtistIdentityCandidateModel.artist_master_id == master.id)
        return ArtistMasterSummary(
            id=master.id,
            canonical_artist_key=master.canonical_artist_key,
            source_artist_slug=master.source_artist_slug,
            display_name=master.display_name,
            normalized_name=master.normalized_name,
            primary_genre_seed=master.primary_genre_seed,
            appearance_count=master.appearance_count,
            is_2026_artist=master.is_2026_artist,
            is_top_artist=master.is_top_artist,
            needs_manual_review=master.needs_manual_review,
            review_status=master.review_status,
            feature_eligibility_status=master.feature_eligibility_status,
            alias_count=alias_count,
            link_count=link_count,
            candidate_count=candidate_count,
        )

    def _alias_record(self, alias: ArtistAliasModel) -> ArtistAliasRecord:
        return ArtistAliasRecord(
            id=alias.id,
            alias=alias.alias,
            normalized_alias=alias.normalized_alias,
            alias_type=alias.alias_type,
            source_key=alias.source_key,
            confidence=alias.confidence,
            status=alias.status,
        )

    def _link_record(self, link: ArtistIdentityLinkModel) -> ArtistIdentityLinkRecord:
        return ArtistIdentityLinkRecord(
            id=link.id,
            platform=link.platform,
            profile_name=link.profile_name,
            normalized_profile_name=link.normalized_profile_name,
            profile_url=link.profile_url,
            external_id=link.external_id,
            confidence=link.confidence,
            confidence_score=link.confidence_score,
            match_status=link.match_status,
            match_method=link.match_method,
            is_primary=link.is_primary,
            is_feature_eligible=link.is_feature_eligible,
            requires_manual_review=link.requires_manual_review,
            source_table=link.source_table,
            source_record_id=link.source_record_id,
        )

    def _candidate_record(self, row: ArtistIdentityCandidateModel) -> ArtistIdentityCandidateRecord:
        return ArtistIdentityCandidateRecord(
            id=row.id,
            artist_master_id=row.artist_master_id,
            canonical_artist_key=row.canonical_artist_key,
            candidate_key=row.candidate_key,
            platform=row.platform,
            candidate_name=row.candidate_name,
            normalized_candidate_name=row.normalized_candidate_name,
            candidate_url=row.candidate_url,
            external_id=row.external_id,
            match_score=row.match_score,
            confidence=row.confidence,
            status=row.status,
            suggested_action=row.suggested_action,
            match_method=row.match_method,
            source_table=row.source_table,
            source_record_id=row.source_record_id,
            evidence_payload=row.evidence_payload,
            review_notes=row.review_notes,
        )
