"""Spotify Developer API integration for Nexus Predictor V2.2.

The service uses Spotify's Client Credentials flow for server-to-server access
to public catalog data. It never stores client secrets in the database or API
responses. Public values are stored in PostgreSQL and duplicated into the V2
evidence layer so later demand features remain traceable.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    ArtistModel,
    ArtistMetricModel,
    EvidenceItemModel,
    PlatformProfileModel,
    SourceModel,
    SpotifyArtistCacheModel,
)
from app.schemas.spotify import (
    SpotifyArtistCacheRecord,
    SpotifyArtistSearchResult,
    SpotifyRefreshBatchResult,
    SpotifyRefreshResult,
    SpotifyReleaseRecord,
    SpotifyStatus,
    SpotifyTrackRecord,
)
from app.services.evidence_seed_service import (
    create_evidence,
    dumps_json,
    get_or_create_source,
    upsert_artist_metric,
)
from app.services.external_http_service import ExternalServiceError


def utc_now() -> datetime:
    """Return a timezone-naive UTC datetime for consistency with existing rows."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def load_json_list(value: str | None) -> list[Any]:
    """Decode a JSON list stored in a Text column."""
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def load_json_object(value: str | None) -> dict[str, Any]:
    """Decode a JSON object stored in a Text column."""
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def normalize_name(value: str) -> str:
    """Normalize artist names for matching without overfitting."""
    return " ".join(value.lower().replace("&", "and").replace(".", "").split())


class SpotifyCredentialsMissingError(ExternalServiceError):
    """Raised when a Spotify action requires missing client credentials."""


class SpotifyService:
    """Low-level Spotify Web API client plus V2 cache/evidence operations."""

    def __init__(self) -> None:
        """Create an in-memory token cache for this process."""
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    @property
    def configured(self) -> bool:
        """Return true only when both Spotify credentials are configured."""
        return settings.spotify_configured

    def status(self) -> SpotifyStatus:
        """Return a safe public configuration status."""
        return SpotifyStatus(
            configured=self.configured,
            token_url=settings.SPOTIFY_TOKEN_URL,
            api_base_url=settings.SPOTIFY_API_BASE_URL,
            default_market=settings.spotify_default_market,
            artist_search_limit=settings.SPOTIFY_ARTIST_SEARCH_LIMIT,
            top_track_limit=settings.SPOTIFY_TOP_TRACK_LIMIT,
            release_limit=settings.SPOTIFY_RELEASE_LIMIT,
            credentials_hint=(
                "Spotify credentials detected."
                if self.configured
                else "Spotify API credentials are not configured in the backend environment."
            ),
        )

    def _require_configured(self) -> None:
        """Raise a controlled error when credentials are missing."""
        if not self.configured:
            raise SpotifyCredentialsMissingError(
                "Spotify credentials are missing. Configure the backend Spotify API credentials before refreshing."
            )

    def _get_access_token(self) -> str:
        """Return a valid Spotify access token using Client Credentials."""
        self._require_configured()
        now = utc_now()
        if self._access_token and self._token_expires_at and self._token_expires_at > now + timedelta(seconds=30):
            return self._access_token

        try:
            with httpx.Client(timeout=settings.external_timeout) as client:
                response = client.post(
                    settings.SPOTIFY_TOKEN_URL,
                    data={"grant_type": "client_credentials"},
                    auth=(settings.SPOTIFY_CLIENT_ID or "", settings.SPOTIFY_CLIENT_SECRET or ""),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Spotify token request failed: {exc}") from exc
        except ValueError as exc:
            raise ExternalServiceError("Spotify token response was not valid JSON.") from exc

        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        if not token:
            raise ExternalServiceError("Spotify token response did not include access_token.")

        self._access_token = str(token)
        self._token_expires_at = now + timedelta(seconds=expires_in)
        return self._access_token

    def _request(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform an authenticated GET request against the Spotify Web API.

        The public error message intentionally avoids tokens, secrets or full
        authorization details. Some Spotify endpoints can return 403 for newly
        created/development apps depending on Spotify platform restrictions;
        callers decide whether a denied endpoint is critical or optional.
        """
        token = self._get_access_token()
        url = f"{settings.SPOTIFY_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        safe_path = path if path.startswith("/") else f"/{path}"
        try:
            with httpx.Client(timeout=settings.external_timeout) as client:
                response = client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                retry_after = exc.response.headers.get("Retry-After", "unknown")
                raise ExternalServiceError(f"Spotify rate limit reached. Retry-After={retry_after}.") from exc
            if exc.response.status_code == 403:
                raise ExternalServiceError(
                    f"Spotify API denied access to {safe_path}. "
                    "This endpoint may be restricted for this Spotify app, market or quota mode."
                ) from exc
            raise ExternalServiceError(
                f"Spotify API request failed for {safe_path} with status {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Spotify API request failed for {safe_path}: {exc}") from exc
        except ValueError as exc:
            raise ExternalServiceError("Spotify API returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ExternalServiceError("Spotify API returned an unexpected payload.")
        return payload

    def search_artist_candidates(self, artist_name: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        """Return Spotify artist candidates for a Nexus artist name."""
        payload = self._request(
            "/search",
            params={
                "q": artist_name,
                "type": "artist",
                "limit": limit or settings.SPOTIFY_ARTIST_SEARCH_LIMIT,
                "market": settings.spotify_default_market,
            },
        )
        items = (((payload.get("artists") or {}).get("items")) or [])
        return [item for item in items if isinstance(item, dict)]

    def search_artist(self, artist_name: str) -> dict[str, Any] | None:
        """Return the best Spotify artist match for compatibility with V1 code."""
        candidates = self.search_artist_candidates(artist_name)
        ranked = self.rank_artist_candidates(artist_name, candidates)
        return ranked[0].raw if ranked else None

    def rank_artist_candidates(self, requested_name: str, candidates: list[dict[str, Any]]) -> list[SpotifyArtistSearchResult]:
        """Score candidates using name similarity and popularity."""
        requested_normalized = normalize_name(requested_name)
        ranked: list[SpotifyArtistSearchResult] = []

        for candidate in candidates:
            candidate_name = str(candidate.get("name") or "")
            candidate_normalized = normalize_name(candidate_name)
            name_score = SequenceMatcher(None, requested_normalized, candidate_normalized).ratio()
            popularity = candidate.get("popularity")
            popularity_score = (float(popularity) / 100.0) if isinstance(popularity, int) else 0.0
            exact_bonus = 0.25 if requested_normalized == candidate_normalized else 0.0
            score = round(min(1.0, name_score * 0.75 + popularity_score * 0.20 + exact_bonus), 4)

            ranked.append(
                SpotifyArtistSearchResult(
                    spotify_artist_id=str(candidate.get("id") or ""),
                    name=candidate_name,
                    popularity=popularity if isinstance(popularity, int) else None,
                    followers=(candidate.get("followers") or {}).get("total"),
                    genres=list(candidate.get("genres") or []),
                    spotify_url=(candidate.get("external_urls") or {}).get("spotify"),
                    score=score,
                    raw=candidate,
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    def get_artist_top_tracks(self, spotify_artist_id: str, *, market: str | None = None) -> list[dict[str, Any]]:
        """Return top tracks for a Spotify artist."""
        payload = self._request(
            f"/artists/{spotify_artist_id}/top-tracks",
            params={"market": market or settings.spotify_default_market},
        )
        tracks = payload.get("tracks") or []
        return [track for track in tracks if isinstance(track, dict)][: settings.SPOTIFY_TOP_TRACK_LIMIT]

    def get_recent_releases(self, spotify_artist_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        """Return recent releases/albums/singles for a Spotify artist."""
        payload = self._request(
            f"/artists/{spotify_artist_id}/albums",
            params={
                "include_groups": "album,single,appears_on,compilation",
                "limit": limit or settings.SPOTIFY_RELEASE_LIMIT,
                "market": settings.spotify_default_market,
            },
        )
        releases = payload.get("items") or []
        return [release for release in releases if isinstance(release, dict)]

    @staticmethod
    def profile_from_artist(artist: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify artist payload into the legacy profile contract."""
        images = artist.get("images") or []
        image_url = images[0].get("url") if images and isinstance(images[0], dict) else None
        spotify_id = artist.get("id")
        return {
            "spotify_id": spotify_id,
            "spotify_url": (artist.get("external_urls") or {}).get("spotify"),
            "spotify_uri": artist.get("uri"),
            "embed_url": f"https://open.spotify.com/embed/artist/{spotify_id}" if spotify_id else None,
            "image_url": image_url,
            "popularity": artist.get("popularity"),
            "followers": (artist.get("followers") or {}).get("total"),
            "genres": list(artist.get("genres") or []),
        }

    @staticmethod
    def track_from_spotify(track: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify track payload into the legacy profile track contract."""
        album = track.get("album") or {}
        return {
            "title": track.get("name"),
            "artist": ", ".join(artist.get("name", "") for artist in track.get("artists", []) if artist.get("name")),
            "source": "spotify",
            "source_url": (track.get("external_urls") or {}).get("spotify"),
            "preview_url": track.get("preview_url"),
            "popularity": track.get("popularity"),
            "album": album.get("name"),
            "release_date": album.get("release_date"),
        }

    @staticmethod
    def release_from_spotify(release: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify album/release payload into the legacy release contract."""
        images = release.get("images") or []
        image_url = images[0].get("url") if images and isinstance(images[0], dict) else None
        return {
            "title": release.get("name"),
            "source": "spotify",
            "source_url": (release.get("external_urls") or {}).get("spotify"),
            "release_type": release.get("album_type") or release.get("type"),
            "release_date": release.get("release_date"),
            "image_url": image_url,
            "total_tracks": release.get("total_tracks"),
        }

    @staticmethod
    def track_record_from_spotify(track: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify track payload into the V2 cache contract."""
        album = track.get("album") or {}
        return SpotifyTrackRecord(
            id=track.get("id"),
            title=str(track.get("name") or "Unknown track"),
            popularity=track.get("popularity") if isinstance(track.get("popularity"), int) else None,
            preview_url=track.get("preview_url"),
            spotify_url=(track.get("external_urls") or {}).get("spotify"),
            album_name=album.get("name"),
            release_date=album.get("release_date"),
            duration_ms=track.get("duration_ms") if isinstance(track.get("duration_ms"), int) else None,
            explicit=track.get("explicit") if isinstance(track.get("explicit"), bool) else None,
        ).model_dump()

    @staticmethod
    def release_record_from_spotify(release: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify release payload into the V2 cache contract."""
        images = release.get("images") or []
        image_url = images[0].get("url") if images and isinstance(images[0], dict) else None
        return SpotifyReleaseRecord(
            id=release.get("id"),
            title=str(release.get("name") or "Unknown release"),
            release_type=release.get("album_type") or release.get("type"),
            release_date=release.get("release_date"),
            total_tracks=release.get("total_tracks") if isinstance(release.get("total_tracks"), int) else None,
            spotify_url=(release.get("external_urls") or {}).get("spotify"),
            image_url=image_url,
        ).model_dump()

    def get_cached_artist(self, db: Session, artist_slug: str) -> SpotifyArtistCacheRecord | None:
        """Return a cached Spotify artist by Nexus slug."""
        cache = db.scalar(select(SpotifyArtistCacheModel).where(SpotifyArtistCacheModel.artist_slug == artist_slug))
        return self.cache_record(cache) if cache else None

    def refresh_artist(
        self,
        db: Session,
        artist_slug: str,
        *,
        force: bool = False,
        market: str | None = None,
    ) -> SpotifyRefreshResult:
        """Refresh one Nexus artist from Spotify and store cache/evidence."""
        if not self.configured:
            return SpotifyRefreshResult(
                artist_slug=artist_slug,
                refreshed=False,
                cached=False,
                configured=False,
                message="Spotify credentials are missing.",
                warnings=[
                    "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in backend/.env, then restart the backend."
                ],
            )

        artist = db.scalar(select(ArtistModel).where(ArtistModel.slug == artist_slug))
        if artist is None:
            return SpotifyRefreshResult(
                artist_slug=artist_slug,
                refreshed=False,
                cached=False,
                configured=True,
                message=f"Artist {artist_slug} was not found.",
                warnings=[f"Unknown artist slug: {artist_slug}"],
            )

        existing = db.scalar(select(SpotifyArtistCacheModel).where(SpotifyArtistCacheModel.artist_slug == artist_slug))
        if existing is not None and not force:
            return SpotifyRefreshResult(
                artist_slug=artist_slug,
                refreshed=False,
                cached=True,
                configured=True,
                message="Spotify artist already cached. Use force=true to refresh.",
                spotify_artist=self.cache_record(existing),
            )

        candidates = self.search_artist_candidates(artist.name)
        ranked_candidates = self.rank_artist_candidates(artist.name, candidates)
        if not ranked_candidates:
            return SpotifyRefreshResult(
                artist_slug=artist_slug,
                refreshed=False,
                cached=False,
                configured=True,
                message="Spotify did not return an artist match.",
                warnings=[f"No Spotify artist candidate found for {artist.name}."],
            )

        best = ranked_candidates[0]
        if best.score < 0.55:
            return SpotifyRefreshResult(
                artist_slug=artist_slug,
                refreshed=False,
                cached=False,
                configured=True,
                message="Spotify match confidence was too low.",
                warnings=[f"Best match {best.name} scored {best.score}; manual review recommended."],
            )

        spotify_artist = best.raw
        spotify_id = best.spotify_artist_id
        warnings: list[str] = []

        # Spotify can deny optional catalog sub-endpoints for newly created or
        # development-mode apps. Artist matching/profile fields are still useful
        # and should be cached as evidence, so top tracks/releases must not make
        # the whole refresh fail when they are unavailable.
        try:
            top_tracks = [
                self.track_record_from_spotify(track)
                for track in self.get_artist_top_tracks(spotify_id, market=market)
            ]
        except ExternalServiceError as exc:
            top_tracks = []
            warnings.append(
                "Spotify top tracks could not be collected for this artist. "
                f"Continuing with artist profile data. Reason: {exc}"
            )

        try:
            releases = [
                self.release_record_from_spotify(release)
                for release in self.get_recent_releases(spotify_id)
            ]
        except ExternalServiceError as exc:
            releases = []
            warnings.append(
                "Spotify releases could not be collected for this artist. "
                f"Continuing with artist profile data. Reason: {exc}"
            )

        profile = self.profile_from_artist(spotify_artist)
        now = utc_now()
        match_confidence = "high" if best.score >= 0.86 else "medium"

        if existing is None:
            existing = SpotifyArtistCacheModel(
                artist_id=artist.id,
                artist_slug=artist.slug,
                spotify_artist_id=spotify_id,
                name=best.name,
            )
            db.add(existing)

        existing.artist_id = artist.id
        existing.spotify_artist_id = spotify_id
        existing.spotify_url = profile.get("spotify_url")
        existing.spotify_uri = profile.get("spotify_uri")
        existing.embed_url = profile.get("embed_url")
        existing.name = best.name
        existing.avatar_url = profile.get("image_url")
        existing.popularity = profile.get("popularity")
        existing.followers = profile.get("followers")
        existing.genres_json = dumps_json(profile.get("genres") or [])
        existing.top_tracks_json = dumps_json(top_tracks)
        existing.releases_json = dumps_json(releases)
        existing.raw_json = dumps_json(
            {
                "artist": spotify_artist,
                "ranked_candidates": [candidate.model_dump() for candidate in ranked_candidates],
                "warnings": warnings,
            }
        )
        existing.match_confidence = match_confidence
        existing.match_method = "spotify_search_client_credentials"
        existing.last_refreshed_at = now
        existing.updated_at = now
        db.flush()

        source = get_or_create_source(
            db,
            key="spotify_api",
            name="Spotify Web API",
            source_type="music_platform",
            base_url="https://open.spotify.com/",
            confidence="high",
            extraction_method="api",
            notes="Spotify public catalog data captured through Client Credentials.",
            raw={"provider": "spotify", "block": "V2.2"},
        )

        evidence_count = self._store_spotify_evidence(
            db,
            artist=artist,
            source=source,
            cache=existing,
            spotify_artist=spotify_artist,
            top_tracks=top_tracks,
            releases=releases,
        )

        metrics_count = self._store_spotify_metrics(
            db,
            artist=artist,
            profile=profile,
            top_tracks=top_tracks,
            releases=releases,
            match_confidence=match_confidence,
        )

        self._upsert_platform_profile(db, artist=artist, cache=existing, evidence_source=source)

        db.commit()
        db.refresh(existing)

        return SpotifyRefreshResult(
            artist_slug=artist_slug,
            refreshed=True,
            cached=True,
            configured=True,
            message=f"Spotify enrichment refreshed for {artist_slug}.",
            spotify_artist=self.cache_record(existing),
            evidence_items_created=evidence_count,
            metrics_upserted=metrics_count,
            warnings=warnings,
        )

    def refresh_top_artists(self, db: Session, *, limit: int = 10, force: bool = False) -> SpotifyRefreshBatchResult:
        """Refresh artists ordered by Nexus appearance count."""
        artists = list(
            db.scalars(
                select(ArtistModel)
                .order_by(ArtistModel.appearance_count.desc(), ArtistModel.name.asc())
                .limit(max(1, min(limit, 50)))
            )
        )

        results: list[SpotifyRefreshResult] = []
        errors: list[str] = []
        for artist in artists:
            try:
                results.append(self.refresh_artist(db, artist.slug, force=force))
            except ExternalServiceError as exc:
                errors.append(f"{artist.slug}: {exc}")
                results.append(
                    SpotifyRefreshResult(
                        artist_slug=artist.slug,
                        refreshed=False,
                        cached=False,
                        configured=self.configured,
                        message="Spotify refresh failed.",
                        warnings=[str(exc)],
                    )
                )

        return SpotifyRefreshBatchResult(
            requested=len(artists),
            refreshed=sum(1 for result in results if result.refreshed),
            skipped=sum(1 for result in results if not result.refreshed and not result.warnings),
            failed=sum(1 for result in results if result.warnings and not result.refreshed),
            results=results,
            errors=errors,
        )

    def _store_spotify_evidence(
        self,
        db: Session,
        *,
        artist: ArtistModel,
        source: SourceModel,
        cache: SpotifyArtistCacheModel,
        spotify_artist: dict[str, Any],
        top_tracks: list[dict[str, Any]],
        releases: list[dict[str, Any]],
    ) -> int:
        """Create atomic evidence rows for the Spotify payload."""
        created = 0
        evidence_payloads: list[tuple[str, Any, str, str]] = [
            ("spotify.artist_id", cache.spotify_artist_id, "text", "Matched Spotify artist id."),
            ("spotify.artist_url", cache.spotify_url, "url", "Public Spotify artist URL."),
            ("spotify.embed_url", cache.embed_url, "url", "Spotify artist embed URL prepared for the frontend."),
            ("spotify.avatar_url", cache.avatar_url, "url", "Primary Spotify artist image."),
            ("spotify.popularity", cache.popularity, "number", "Spotify popularity score, 0-100."),
            ("spotify.followers", cache.followers, "number", "Spotify public follower count."),
            ("spotify.genres", load_json_list(cache.genres_json), "json", "Spotify genre labels."),
            ("spotify.top_tracks", top_tracks, "json", "Spotify top tracks snapshot."),
            ("spotify.releases", releases, "json", "Spotify recent releases snapshot."),
        ]

        for metric_key, metric_value, value_type, notes in evidence_payloads:
            if metric_value in (None, "", [], {}):
                continue
            create_evidence(
                db,
                artist=artist,
                source=source,
                metric_key=metric_key,
                metric_value=metric_value,
                value_type=value_type,
                confidence=cache.match_confidence,
                extraction_method="api",
                evidence_kind="music_platform_profile",
                status="official",
                notes=notes,
                source_url=cache.spotify_url,
                raw={"spotify_artist": spotify_artist if metric_key == "spotify.artist_id" else None},
            )
            created += 1

        return created

    def _store_spotify_metrics(
        self,
        db: Session,
        *,
        artist: ArtistModel,
        profile: dict[str, Any],
        top_tracks: list[dict[str, Any]],
        releases: list[dict[str, Any]],
        match_confidence: str,
    ) -> int:
        """Upsert derived artist metrics backed by Spotify evidence."""
        metrics = [
            {
                "metric_key": "spotify_popularity",
                "numeric_value": profile.get("popularity"),
                "value_type": "number",
                "notes": "Spotify popularity score, 0-100.",
            },
            {
                "metric_key": "spotify_followers",
                "numeric_value": profile.get("followers"),
                "value_type": "number",
                "notes": "Spotify public follower count.",
            },
            {
                "metric_key": "spotify_top_track_count",
                "numeric_value": float(len(top_tracks)),
                "value_type": "number",
                "notes": "Number of cached Spotify top tracks.",
            },
            {
                "metric_key": "spotify_release_count",
                "numeric_value": float(len(releases)),
                "value_type": "number",
                "notes": "Number of cached Spotify releases.",
            },
            {
                "metric_key": "spotify_genres",
                "text_value": ", ".join(profile.get("genres") or []),
                "value_type": "text",
                "notes": "Spotify genre labels joined for searchable features.",
            },
        ]

        upserted = 0
        for metric in metrics:
            numeric_value = metric.get("numeric_value")
            text_value = metric.get("text_value")
            if numeric_value is None and not text_value:
                continue
            upsert_artist_metric(
                db,
                artist=artist,
                metric_key=str(metric["metric_key"]),
                numeric_value=float(numeric_value) if numeric_value is not None else None,
                text_value=str(text_value) if text_value else None,
                value_type=str(metric["value_type"]),
                confidence=match_confidence,
                evidence_count=1,
                notes=str(metric["notes"]),
                raw={"provider": "spotify"},
            )
            upserted += 1

        return upserted

    def _upsert_platform_profile(
        self,
        db: Session,
        *,
        artist: ArtistModel,
        cache: SpotifyArtistCacheModel,
        evidence_source: SourceModel,
    ) -> None:
        """Create or update the generic platform profile row for Spotify."""
        profile = db.scalar(
            select(PlatformProfileModel).where(
                PlatformProfileModel.artist_slug == artist.slug,
                PlatformProfileModel.platform == "spotify",
            )
        )
        if profile is None:
            profile = PlatformProfileModel(
                artist_id=artist.id,
                artist_slug=artist.slug,
                platform="spotify",
                raw_json="{}",
            )
            db.add(profile)

        profile.artist_id = artist.id
        profile.profile_name = cache.name
        profile.profile_url = cache.spotify_url
        profile.external_id = cache.spotify_artist_id
        profile.is_official = cache.match_confidence in {"high", "verified"}
        profile.confidence = cache.match_confidence
        profile.raw_json = dumps_json(
            {
                "source_id": evidence_source.id,
                "embed_url": cache.embed_url,
                "popularity": cache.popularity,
                "followers": cache.followers,
            }
        )

    @staticmethod
    def cache_record(cache: SpotifyArtistCacheModel) -> SpotifyArtistCacheRecord:
        """Map a SQLAlchemy cache row into the API schema."""
        return SpotifyArtistCacheRecord(
            id=cache.id,
            artist_slug=cache.artist_slug,
            spotify_artist_id=cache.spotify_artist_id,
            spotify_url=cache.spotify_url,
            spotify_uri=cache.spotify_uri,
            embed_url=cache.embed_url,
            name=cache.name,
            avatar_url=cache.avatar_url,
            popularity=cache.popularity,
            followers=cache.followers,
            genres=load_json_list(cache.genres_json),
            top_tracks=[SpotifyTrackRecord(**item) for item in load_json_list(cache.top_tracks_json)],
            releases=[SpotifyReleaseRecord(**item) for item in load_json_list(cache.releases_json)],
            match_confidence=cache.match_confidence,
            match_method=cache.match_method,
            last_refreshed_at=cache.last_refreshed_at,
        )
