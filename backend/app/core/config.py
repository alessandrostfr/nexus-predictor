"""Application settings for Nexus Predictor V2.

V2 centralizes environment variables because the backend now depends on
PostgreSQL, Alembic, evidence tracking and external providers such as Spotify.
No secret should be committed; real credentials live only in `.env`.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or `.env`."""

    APP_NAME: str = "Nexus Predictor"
    APP_VERSION: str = "2.2.0-spotify"
    ENVIRONMENT: str = "development"

    # PostgreSQL is the official V2 database. SQLite remains useful for tiny
    # local experiments if the variable is changed manually.
    DATABASE_URL: str = "postgresql+psycopg://nexus:nexus@localhost:5432/nexus_predictor"

    # FastAPI local frontend access.
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    # V2 official workflow is Alembic. These switches keep old dev/test flows
    # safe without turning create_all into the default migration strategy.
    AUTO_CREATE_DATABASE_SCHEMA: bool = False
    AUTO_SEED_DATABASE: bool = True

    # External enrichment guard used by the older V1 artist profile endpoint.
    ENABLE_EXTERNAL_ARTIST_ENRICHMENT: bool = False

    # Shared external request configuration.
    EXTERNAL_REQUEST_TIMEOUT_SECONDS: float = 20.0
    MUSICBRAINZ_USER_AGENT: str = "NexusPredictor/2.2 (local research app)"

    # Last.fm remains optional from the V1 enrichment foundation. It is not part
    # of V2.2, but keeping the setting prevents legacy imports from breaking.
    LASTFM_API_KEY: str | None = None

    # Spotify V2.2. Leave empty locally until credentials are created in the
    # Spotify Developer Dashboard.
    SPOTIFY_CLIENT_ID: str | None = None
    SPOTIFY_CLIENT_SECRET: str | None = None
    SPOTIFY_TOKEN_URL: str = "https://accounts.spotify.com/api/token"
    SPOTIFY_API_BASE_URL: str = "https://api.spotify.com/v1"
    SPOTIFY_DEFAULT_MARKET: str = "ES"
    SPOTIFY_ARTIST_SEARCH_LIMIT: int = 5
    SPOTIFY_TOP_TRACK_LIMIT: int = 10
    SPOTIFY_RELEASE_LIMIT: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a clean list for FastAPI middleware."""
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def safe_database_url(self) -> str:
        """Return the configured database URL without leaking the password."""
        try:
            parts = urlsplit(self.DATABASE_URL)
            if not parts.password:
                return self.DATABASE_URL

            username = parts.username or ""
            hostname = parts.hostname or ""
            port = f":{parts.port}" if parts.port else ""
            safe_netloc = f"{username}:***@{hostname}{port}" if username else f"***@{hostname}{port}"
            return urlunsplit((parts.scheme, safe_netloc, parts.path, parts.query, parts.fragment))
        except ValueError:
            return "<invalid database url>"

    @property
    def external_timeout(self) -> float:
        """Compatibility alias used by older external HTTP helpers."""
        return self.EXTERNAL_REQUEST_TIMEOUT_SECONDS

    @property
    def musicbrainz_user_agent(self) -> str:
        """Compatibility alias for the MusicBrainz client."""
        return self.MUSICBRAINZ_USER_AGENT

    @property
    def lastfm_api_key(self) -> str | None:
        """Compatibility alias for the optional Last.fm client."""
        return self.LASTFM_API_KEY

    @property
    def spotify_configured(self) -> bool:
        """Return true only when both Spotify client credentials are present."""
        return bool(self.SPOTIFY_CLIENT_ID and self.SPOTIFY_CLIENT_SECRET)

    @property
    def spotify_default_market(self) -> str:
        """Return the configured Spotify market in uppercase format."""
        return (self.SPOTIFY_DEFAULT_MARKET or "ES").upper()


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
