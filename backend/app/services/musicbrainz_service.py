"""MusicBrainz metadata client for aliases, country and releases."""

from typing import Any

from app.core.config import settings
from app.services.external_http_service import request_json


class MusicBrainzService:
    """Minimal MusicBrainz API client with respectful headers."""

    api_base_url = "https://musicbrainz.org/ws/2"

    def _headers(self) -> dict[str, str]:
        """Return MusicBrainz headers including a descriptive User-Agent."""
        return {"User-Agent": settings.musicbrainz_user_agent}

    def search_artist(self, artist_name: str) -> dict[str, Any] | None:
        """Find the most relevant MusicBrainz artist by name."""
        payload = request_json(
            "GET",
            f"{self.api_base_url}/artist/",
            headers=self._headers(),
            params={"query": f'artist:"{artist_name}"', "fmt": "json", "limit": 1},
        )
        artists = payload.get("artists") or []
        return artists[0] if artists else None

    def get_recent_releases(self, musicbrainz_artist_id: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return recent release groups for an artist."""
        payload = request_json(
            "GET",
            f"{self.api_base_url}/release-group/",
            headers=self._headers(),
            params={
                "artist": musicbrainz_artist_id,
                "fmt": "json",
                "limit": min(limit, 10),
                "type": "album|single|ep",
            },
        )
        releases = list(payload.get("release-groups") or [])
        releases.sort(key=lambda item: str(item.get("first-release-date") or ""), reverse=True)
        return releases[:limit]

    @staticmethod
    def profile_from_artist(artist: dict[str, Any]) -> dict[str, Any]:
        """Map a MusicBrainz artist into internal profile fields."""
        aliases = []
        for alias in artist.get("aliases") or []:
            name = alias.get("name")
            if name and name not in aliases:
                aliases.append(name)
        return {
            "musicbrainz_id": artist.get("id"),
            "country": artist.get("country") or artist.get("area", {}).get("name"),
            "aliases": aliases,
            "musicbrainz_url": f"https://musicbrainz.org/artist/{artist.get('id')}" if artist.get("id") else None,
        }

    @staticmethod
    def release_from_musicbrainz(release: dict[str, Any]) -> dict[str, Any]:
        """Map a MusicBrainz release group into the internal release shape."""
        release_id = release.get("id")
        return {
            "title": release.get("title", "Unknown release"),
            "release_type": release.get("primary-type"),
            "release_date": release.get("first-release-date"),
            "source": "musicbrainz",
            "external_url": f"https://musicbrainz.org/release-group/{release_id}" if release_id else None,
        }
