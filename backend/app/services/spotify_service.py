"""Spotify metadata client for artist profile enrichment.

Spotify is used only for profile display fields such as image, links, top tracks
and recent releases. The prediction model must not train on Spotify-only content.
"""

import base64
from typing import Any

from app.core.config import settings
from app.services.external_http_service import ExternalServiceError, request_json


class SpotifyService:
    """Minimal Spotify Web API client using the Client Credentials flow."""

    token_url = "https://accounts.spotify.com/api/token"
    api_base_url = "https://api.spotify.com/v1"

    def __init__(self) -> None:
        """Initialize the service without making network calls."""
        self._access_token: str | None = None

    @property
    def configured(self) -> bool:
        """Return whether Spotify credentials are available."""
        return bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET)

    def get_access_token(self) -> str:
        """Request and cache a short-lived Spotify access token."""
        if not self.configured:
            raise ExternalServiceError("Spotify credentials are not configured.")
        if self._access_token:
            return self._access_token

        credentials = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode("utf-8")
        encoded_credentials = base64.b64encode(credentials).decode("utf-8")
        payload = request_json(
            "POST",
            self.token_url,
            headers={"Authorization": f"Basic {encoded_credentials}"},
            data={"grant_type": "client_credentials"},
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise ExternalServiceError("Spotify token response did not contain an access token.")
        self._access_token = token
        return token

    def _headers(self) -> dict[str, str]:
        """Return authorization headers for Spotify API calls."""
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    def search_artist(self, artist_name: str) -> dict[str, Any] | None:
        """Find the most relevant Spotify artist match by name."""
        payload = request_json(
            "GET",
            f"{self.api_base_url}/search",
            headers=self._headers(),
            params={"q": artist_name, "type": "artist", "limit": 1},
        )
        items = payload.get("artists", {}).get("items", [])
        return items[0] if items else None

    def get_artist_top_tracks(self, spotify_artist_id: str, *, market: str = "ES") -> list[dict[str, Any]]:
        """Return Spotify top tracks for display purposes."""
        payload = request_json(
            "GET",
            f"{self.api_base_url}/artists/{spotify_artist_id}/top-tracks",
            headers=self._headers(),
            params={"market": market},
        )
        return list(payload.get("tracks", []))[:10]

    def get_recent_releases(self, spotify_artist_id: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return recent albums/singles for display purposes."""
        payload = request_json(
            "GET",
            f"{self.api_base_url}/artists/{spotify_artist_id}/albums",
            headers=self._headers(),
            params={
                "include_groups": "album,single,appears_on,compilation",
                "limit": min(limit, 10),
                "market": "ES",
            },
        )
        releases = list(payload.get("items", []))
        releases.sort(key=lambda item: str(item.get("release_date") or ""), reverse=True)
        return releases[:limit]

    @staticmethod
    def profile_from_artist(spotify_artist: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify artist payload into profile fields."""
        images = spotify_artist.get("images") or []
        external_urls = spotify_artist.get("external_urls") or {}
        return {
            "spotify_id": spotify_artist.get("id"),
            "image_url": images[0].get("url") if images else None,
            "spotify_url": external_urls.get("spotify"),
            "genres": spotify_artist.get("genres") or [],
        }

    @staticmethod
    def track_from_spotify(track: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify track into the internal track shape."""
        album = track.get("album") or {}
        images = album.get("images") or []
        return {
            "title": track.get("name", "Unknown track"),
            "artist_name": ", ".join(artist.get("name", "") for artist in track.get("artists", [])).strip(", "),
            "source": "spotify",
            "album_name": album.get("name"),
            "release_date": album.get("release_date"),
            "external_url": (track.get("external_urls") or {}).get("spotify"),
            "image_url": images[0].get("url") if images else None,
        }

    @staticmethod
    def release_from_spotify(release: dict[str, Any]) -> dict[str, Any]:
        """Map a Spotify release into the internal release shape."""
        images = release.get("images") or []
        return {
            "title": release.get("name", "Unknown release"),
            "release_type": release.get("album_type"),
            "release_date": release.get("release_date"),
            "source": "spotify",
            "external_url": (release.get("external_urls") or {}).get("spotify"),
            "image_url": images[0].get("url") if images else None,
        }
