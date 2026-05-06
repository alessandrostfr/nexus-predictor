"""Artist profile enrichment service.

Block 3 adds a controlled enrichment layer on top of the lineup-based artist
index. It combines the internal SQLite artist seed with a versioned JSON cache
and, only when explicitly enabled, external APIs such as Spotify, Last.fm and
MusicBrainz.
"""

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.paths import ARTIST_PROFILE_CACHE_PATH
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.artist_enrichment import ArtistProfile, ArtistProfileList, ArtistRefreshResult
from app.services.external_http_service import ExternalServiceError
from app.services.lastfm_service import LastFMService
from app.services.musicbrainz_service import MusicBrainzService
from app.services.spotify_service import SpotifyService


def utc_now_iso() -> str:
    """Return an ISO timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


class ArtistEnrichmentService:
    """Build and refresh enriched artist profiles."""

    def __init__(self, db: Session) -> None:
        """Create repositories and external clients for one request/session."""
        self.repository = SQLiteRepository(db)
        self.spotify = SpotifyService()
        self.lastfm = LastFMService()
        self.musicbrainz = MusicBrainzService()

    def list_profiles(
        self,
        *,
        year: int | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ArtistProfileList:
        """Return paginated profiles by merging base artists with cache data."""
        artists = self.repository.list_artists(year=year, query=query, limit=10000, offset=0)["items"]
        profiles = [self.build_profile_from_base_artist(artist) for artist in artists]
        return ArtistProfileList(
            total=len(profiles),
            limit=limit,
            offset=offset,
            items=profiles[offset : offset + limit],
        )

    def get_profile(self, slug: str) -> ArtistProfile | None:
        """Return one enriched profile or `None` when the artist is unknown."""
        artist = self.repository.get_artist(slug)
        if artist is None:
            return None
        return self.build_profile_from_base_artist(artist)

    def refresh_profile(
        self,
        slug: str,
        *,
        use_external_apis: bool = False,
        force: bool = False,
    ) -> ArtistRefreshResult | None:
        """Refresh one artist profile and persist the merged cache entry.

        External calls only run when both `use_external_apis` and the environment
        setting are true. This keeps the normal API deterministic and makes tests
        independent from internet access or private API keys.
        """
        base_artist = self.repository.get_artist(slug)
        if base_artist is None:
            return None

        warnings: list[str] = []
        profile = self.build_profile_from_base_artist(base_artist)
        external_enabled = bool(use_external_apis and settings.ENABLE_EXTERNAL_ARTIST_ENRICHMENT)

        if not external_enabled:
            warnings.append(
                "External artist enrichment is disabled. Set ENABLE_EXTERNAL_ARTIST_ENRICHMENT=true "
                "and pass use_external_apis=true to refresh from APIs."
            )
            profile.enrichment_notes.append("External APIs were not called for this refresh.")
            return ArtistRefreshResult(
                slug=slug,
                refreshed=False,
                external_calls_enabled=False,
                profile=profile,
                warnings=warnings,
            )

        if not force and profile.data_status in {"enriched", "partially_enriched"}:
            warnings.append("Profile already has cached enrichment. Use force=true to refresh it.")
            return ArtistRefreshResult(
                slug=slug,
                refreshed=False,
                external_calls_enabled=True,
                profile=profile,
                warnings=warnings,
            )

        mutable_profile = profile.model_dump()
        mutable_profile["last_enriched_at"] = utc_now_iso()

        self._merge_spotify_data(mutable_profile, warnings)
        self._merge_lastfm_data(mutable_profile, warnings)
        self._merge_musicbrainz_data(mutable_profile, warnings)

        mutable_profile["data_status"] = self._resolve_data_status(mutable_profile)
        merged_profile = ArtistProfile(**mutable_profile)
        self.upsert_cached_profile(merged_profile)
        return ArtistRefreshResult(
            slug=slug,
            refreshed=True,
            external_calls_enabled=True,
            profile=merged_profile,
            warnings=warnings,
        )

    def build_profile_from_base_artist(self, base_artist: dict[str, Any]) -> ArtistProfile:
        """Merge one SQLite artist with its cached enrichment entry."""
        cache = self.load_cache()
        cached_profile = deepcopy((cache.get("profiles") or {}).get(base_artist["slug"], {}))

        base_payload = {
            "slug": base_artist["slug"],
            "name": base_artist["name"],
            "normalized_name": base_artist.get("normalized_name", base_artist["name"]),
            "primary_genre_seed": base_artist.get("primary_genre_seed", "Unknown"),
            "appearance_count": base_artist.get("appearance_count", 0),
            "appearance_years": base_artist.get("appearance_years", []),
            "appearances": base_artist.get("appearances", []),
            "manual_review": base_artist.get("manual_review", False),
            "data_status": "pending_external_enrichment",
            "raw": base_artist.get("raw", {}),
            "enrichment_notes": [
                "Profile is built from the internal lineup dataset until external enrichment is available."
            ],
        }

        merged = self.deep_merge(base_payload, cached_profile)
        return ArtistProfile(**merged)

    def load_cache(self) -> dict[str, Any]:
        """Load the local profile cache, creating an empty structure if needed."""
        if not ARTIST_PROFILE_CACHE_PATH.exists():
            ARTIST_PROFILE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.save_cache({"status": "artist_enrichment_cache", "last_updated_at": None, "profiles": {}})

        with ARTIST_PROFILE_CACHE_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save_cache(self, cache: dict[str, Any]) -> None:
        """Persist the local profile cache with deterministic formatting."""
        ARTIST_PROFILE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ARTIST_PROFILE_CACHE_PATH.open("w", encoding="utf-8") as file:
            json.dump(cache, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")

    def upsert_cached_profile(self, profile: ArtistProfile) -> None:
        """Insert or update one profile in the local JSON cache."""
        cache = self.load_cache()
        profiles = cache.setdefault("profiles", {})
        payload = profile.model_dump()
        payload["last_enriched_at"] = payload.get("last_enriched_at") or utc_now_iso()
        profiles[profile.slug] = payload
        cache["last_updated_at"] = utc_now_iso()
        self.save_cache(cache)

    @staticmethod
    def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Merge dictionaries while preserving base fields not present in cache."""
        result = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = ArtistEnrichmentService.deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _merge_spotify_data(self, profile: dict[str, Any], warnings: list[str]) -> None:
        """Merge Spotify profile fields into the mutable profile payload."""
        if not self.spotify.configured:
            warnings.append("Spotify credentials are missing; Spotify enrichment was skipped.")
            return
        try:
            spotify_artist = self.spotify.search_artist(profile["name"])
            if not spotify_artist:
                warnings.append("Spotify did not return an artist match.")
                return

            spotify_profile = self.spotify.profile_from_artist(spotify_artist)
            profile["external_ids"]["spotify_id"] = spotify_profile.get("spotify_id")
            profile["image_url"] = profile.get("image_url") or spotify_profile.get("image_url")
            if spotify_profile.get("spotify_url"):
                profile["external_links"]["spotify"] = spotify_profile["spotify_url"]
            profile["sources"].append(
                {
                    "source": "spotify",
                    "source_url": spotify_profile.get("spotify_url"),
                    "captured_at": utc_now_iso(),
                    "confidence": "medium",
                    "notes": "Used for artist image, link, top tracks and recent releases display only.",
                }
            )

            top_tracks = [
                self.spotify.track_from_spotify(track)
                for track in self.spotify.get_artist_top_tracks(spotify_profile["spotify_id"])
            ]
            if top_tracks:
                profile["top_tracks"] = self._dedupe_tracks(profile.get("top_tracks", []) + top_tracks)

            latest_releases = [
                self.spotify.release_from_spotify(release)
                for release in self.spotify.get_recent_releases(spotify_profile["spotify_id"])
            ]
            if latest_releases:
                profile["latest_releases"] = self._dedupe_releases(
                    profile.get("latest_releases", []) + latest_releases
                )[:5]
        except ExternalServiceError as exc:
            warnings.append(f"Spotify enrichment failed: {exc}")

    def _merge_lastfm_data(self, profile: dict[str, Any], warnings: list[str]) -> None:
        """Merge Last.fm bio and top tracks into the mutable profile payload."""
        if not self.lastfm.configured:
            warnings.append("Last.fm API key is missing; Last.fm enrichment was skipped.")
            return
        try:
            artist_info = self.lastfm.get_artist_info(profile["name"])
            if artist_info:
                lastfm_bio = self.lastfm.bio_from_lastfm(artist_info)
                profile["external_ids"]["lastfm_name"] = artist_info.get("name") or profile["name"]
                profile["bio"] = profile.get("bio") or lastfm_bio.get("bio")
                profile["bio_source_url"] = profile.get("bio_source_url") or lastfm_bio.get("bio_source_url")
                if artist_info.get("url"):
                    profile["external_links"]["lastfm"] = artist_info["url"]
                profile["sources"].append(
                    {
                        "source": "lastfm",
                        "source_url": artist_info.get("url"),
                        "captured_at": utc_now_iso(),
                        "confidence": "medium",
                        "notes": "Used for public bio, listeners/playcount and top tracks when available.",
                    }
                )

            tracks = [self.lastfm.track_from_lastfm(track) for track in self.lastfm.get_top_tracks(profile["name"])]
            if tracks:
                profile["top_tracks"] = self._dedupe_tracks(profile.get("top_tracks", []) + tracks)[:10]
        except ExternalServiceError as exc:
            warnings.append(f"Last.fm enrichment failed: {exc}")

    def _merge_musicbrainz_data(self, profile: dict[str, Any], warnings: list[str]) -> None:
        """Merge MusicBrainz aliases, country and release metadata."""
        try:
            artist = self.musicbrainz.search_artist(profile["name"])
            if not artist:
                warnings.append("MusicBrainz did not return an artist match.")
                return

            musicbrainz_profile = self.musicbrainz.profile_from_artist(artist)
            profile["external_ids"]["musicbrainz_id"] = musicbrainz_profile.get("musicbrainz_id")
            profile["country"] = profile.get("country") or musicbrainz_profile.get("country")
            profile["aliases"] = sorted(set(profile.get("aliases", []) + musicbrainz_profile.get("aliases", [])))
            if musicbrainz_profile.get("musicbrainz_url"):
                profile["external_links"]["musicbrainz"] = musicbrainz_profile["musicbrainz_url"]
            profile["sources"].append(
                {
                    "source": "musicbrainz",
                    "source_url": musicbrainz_profile.get("musicbrainz_url"),
                    "captured_at": utc_now_iso(),
                    "confidence": "medium",
                    "notes": "Used for aliases, country and release metadata.",
                }
            )

            releases = [
                self.musicbrainz.release_from_musicbrainz(release)
                for release in self.musicbrainz.get_recent_releases(musicbrainz_profile["musicbrainz_id"])
            ]
            if releases:
                profile["latest_releases"] = self._dedupe_releases(
                    profile.get("latest_releases", []) + releases
                )[:5]
        except ExternalServiceError as exc:
            warnings.append(f"MusicBrainz enrichment failed: {exc}")

    @staticmethod
    def _resolve_data_status(profile: dict[str, Any]) -> str:
        """Return a clear status based on populated fields."""
        has_identity = bool(profile.get("image_url") or profile.get("external_links") or profile.get("aliases"))
        has_music = bool(profile.get("top_tracks") or profile.get("latest_releases"))
        has_bio = bool(profile.get("bio"))
        if has_identity and has_music and has_bio:
            return "enriched"
        if has_identity or has_music or has_bio:
            return "partially_enriched"
        return "pending_review"

    @staticmethod
    def _dedupe_tracks(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate tracks while preserving order."""
        seen: set[tuple[str, str | None]] = set()
        deduped = []
        for track in tracks:
            key = (str(track.get("title", "")).lower(), track.get("source"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(track)
        return deduped[:10]

    @staticmethod
    def _dedupe_releases(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate releases while preserving order."""
        seen: set[tuple[str, str | None]] = set()
        deduped = []
        for release in releases:
            key = (str(release.get("title", "")).lower(), release.get("source"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(release)
        return deduped
