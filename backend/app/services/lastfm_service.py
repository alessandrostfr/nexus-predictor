"""Last.fm metadata client for artist profile enrichment."""

from typing import Any

from app.core.config import settings
from app.services.external_http_service import ExternalServiceError, request_json


class LastFMService:
    """Small Last.fm API client for artist bio and top tracks."""

    api_url = "https://ws.audioscrobbler.com/2.0/"

    @property
    def configured(self) -> bool:
        """Return whether a Last.fm API key is available."""
        return bool(settings.LASTFM_API_KEY)

    def _params(self, method: str, artist_name: str, **extra: Any) -> dict[str, Any]:
        """Build common Last.fm query parameters."""
        if not self.configured:
            raise ExternalServiceError("Last.fm API key is not configured.")
        return {
            "method": method,
            "artist": artist_name,
            "api_key": settings.LASTFM_API_KEY,
            "format": "json",
            **extra,
        }

    def get_artist_info(self, artist_name: str) -> dict[str, Any] | None:
        """Return Last.fm artist info or `None` when not found."""
        payload = request_json("GET", self.api_url, params=self._params("artist.getinfo", artist_name))
        artist = payload.get("artist")
        return artist if isinstance(artist, dict) else None

    def get_top_tracks(self, artist_name: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Return Last.fm top tracks for an artist."""
        payload = request_json(
            "GET",
            self.api_url,
            params=self._params("artist.gettoptracks", artist_name, limit=limit),
        )
        tracks = payload.get("toptracks", {}).get("track", [])
        return list(tracks)[:limit]

    @staticmethod
    def bio_from_lastfm(artist: dict[str, Any]) -> dict[str, Any]:
        """Map Last.fm artist info into internal bio fields."""
        bio = artist.get("bio") or {}
        summary = str(bio.get("summary") or "").strip()
        # Last.fm summaries sometimes include HTML links. Keep a clean first part;
        # rich attribution is stored separately in source metadata.
        summary = summary.split("<a ")[0].strip()
        return {
            "bio": summary or None,
            "bio_source_url": artist.get("url"),
            "listeners": int(artist.get("stats", {}).get("listeners", 0) or 0),
            "playcount": int(artist.get("stats", {}).get("playcount", 0) or 0),
        }

    @staticmethod
    def track_from_lastfm(track: dict[str, Any]) -> dict[str, Any]:
        """Map a Last.fm track into the internal track shape."""
        return {
            "title": track.get("name", "Unknown track"),
            "artist_name": (track.get("artist") or {}).get("name") if isinstance(track.get("artist"), dict) else None,
            "source": "lastfm",
            "listeners": int(track.get("listeners", 0) or 0),
            "playcount": int(track.get("playcount", 0) or 0),
            "external_url": track.get("url"),
        }
