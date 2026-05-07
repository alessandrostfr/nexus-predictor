"""Optional Last.fm client kept for legacy V1 artist-profile compatibility.

Last.fm is not part of V2.2. The class remains intentionally small and safe so
old enrichment code can import it without forcing API credentials.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.external_http_service import request_json


class LastFMService:
    """Minimal Last.fm API client.

    It only performs calls when LASTFM_API_KEY is present. Otherwise callers see
    `configured=False` and skip the integration safely.
    """

    api_base_url = "https://ws.audioscrobbler.com/2.0/"

    @property
    def configured(self) -> bool:
        """Return whether the optional Last.fm key exists."""
        return bool(settings.lastfm_api_key)

    def get_artist_info(self, artist_name: str) -> dict[str, Any] | None:
        """Return public artist info from Last.fm when configured."""
        if not self.configured:
            return None
        payload = request_json(
            "GET",
            self.api_base_url,
            params={
                "method": "artist.getinfo",
                "artist": artist_name,
                "api_key": settings.lastfm_api_key,
                "format": "json",
            },
        )
        artist = payload.get("artist")
        return artist if isinstance(artist, dict) else None

    def get_top_tracks(self, artist_name: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return top tracks from Last.fm when configured."""
        if not self.configured:
            return []
        payload = request_json(
            "GET",
            self.api_base_url,
            params={
                "method": "artist.gettoptracks",
                "artist": artist_name,
                "api_key": settings.lastfm_api_key,
                "format": "json",
                "limit": limit,
            },
        )
        tracks = (((payload.get("toptracks") or {}).get("track")) or [])
        return tracks if isinstance(tracks, list) else []

    @staticmethod
    def bio_from_lastfm(artist: dict[str, Any]) -> dict[str, Any]:
        """Map a Last.fm artist payload into the internal profile fields."""
        bio = artist.get("bio") or {}
        return {
            "bio": bio.get("summary"),
            "bio_source_url": artist.get("url"),
            "listeners": artist.get("stats", {}).get("listeners"),
            "playcount": artist.get("stats", {}).get("playcount"),
        }

    @staticmethod
    def track_from_lastfm(track: dict[str, Any]) -> dict[str, Any]:
        """Map a Last.fm track payload into the existing profile contract."""
        return {
            "title": track.get("name"),
            "artist": (track.get("artist") or {}).get("name") if isinstance(track.get("artist"), dict) else None,
            "source": "lastfm",
            "source_url": track.get("url"),
            "playcount": track.get("playcount"),
        }
