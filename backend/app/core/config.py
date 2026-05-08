"""Application settings for the Nexus Predictor backend.

This module centralizes environment-based configuration so the FastAPI app,
database layer, V2 reusable integrations and V3 ML-first collectors can share
one safe settings object.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or `.env`.

    V3.4-A expands the configuration contract for future collectors, but it must
    keep the V2 integration settings alive because Spotify, Last.fm and other
    V2 evidence services are still reused as data sources for V3.
    """

    # ------------------------------------------------------------------
    # Core application settings.
    # ------------------------------------------------------------------
    APP_NAME: str = "Nexus Predictor"
    APP_VERSION: str = "2.0.0-foundations"
    ENVIRONMENT: str = "local"
    DATABASE_URL: str = "postgresql+psycopg://nexus:nexus@localhost:5432/nexus_predictor"
    BACKEND_CORS_ORIGINS: str = (
        "http://127.0.0.1:3000,http://localhost:3000,"
        "http://127.0.0.1:5173,http://localhost:5173"
    )

    # Local development helpers used by the existing database seed flow.
    AUTO_CREATE_DATABASE_SCHEMA: bool = False
    AUTO_SEED_DATABASE: bool = False

    # ------------------------------------------------------------------
    # V2/V3 external enrichment feature flags.
    # ------------------------------------------------------------------
    ENABLE_EXTERNAL_ARTIST_ENRICHMENT: bool = False
    EXTERNAL_TIMEOUT_SECONDS: float = 12.0

    # ------------------------------------------------------------------
    # Spotify V2.2 reusable integration settings.
    #
    # Keep these uppercase fields because Pydantic reads env vars directly from
    # them, and keep lower-case compatibility properties below because the V2
    # Spotify service historically uses both styles.
    # ------------------------------------------------------------------
    SPOTIFY_CLIENT_ID: str | None = None
    SPOTIFY_CLIENT_SECRET: str | None = None
    SPOTIFY_TOKEN_URL: str = "https://accounts.spotify.com/api/token"
    SPOTIFY_API_BASE_URL: str = "https://api.spotify.com/v1"
    SPOTIFY_DEFAULT_MARKET: str = "ES"
    SPOTIFY_ARTIST_SEARCH_LIMIT: int = 5
    SPOTIFY_TOP_TRACK_LIMIT: int = 10
    SPOTIFY_RELEASE_LIMIT: int = 10

    # ------------------------------------------------------------------
    # Last.fm reusable integration settings.
    # ------------------------------------------------------------------
    LASTFM_API_KEY: str | None = None
    LASTFM_API_BASE_URL: str = "https://ws.audioscrobbler.com/2.0/"
    LASTFM_TOP_TRACK_LIMIT: int = 10
    LASTFM_USER_AGENT: str = "NexusPredictorV3/0.1 (local educational ML project)"

    # ------------------------------------------------------------------
    # V3.4 official API / collector configuration.
    # Values are never exposed through public status endpoints.
    # ------------------------------------------------------------------
    YOUTUBE_API_KEY: str | None = None
    SOUNDCLOUD_CLIENT_ID: str | None = None
    SOUNDCLOUD_CLIENT_SECRET: str | None = None
    MUSICBRAINZ_USER_AGENT: str = (
        "NexusPredictorV3/0.1 "
        "(local educational ML project; contact: your-email@example.com)"
    )
    ENABLE_YTDLP_METADATA_COLLECTOR: bool = False

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
        """Return a database URL safe enough for diagnostics.

        The default local URL is not treated as a production secret here. If the
        project later uses production credentials, this helper is the place to
        mask them consistently.
        """
        return self.DATABASE_URL

    @property
    def external_timeout(self) -> float:
        """Return the default timeout used by external HTTP helpers."""
        return self.EXTERNAL_TIMEOUT_SECONDS

    @property
    def musicbrainz_user_agent(self) -> str:
        """Return the configured MusicBrainz User-Agent."""
        return self.MUSICBRAINZ_USER_AGENT

    # ------------------------------------------------------------------
    # Safe credential status helpers.
    # ------------------------------------------------------------------
    @property
    def spotify_configured(self) -> bool:
        """Return whether Spotify credentials are configured without exposing them."""
        return bool(self.SPOTIFY_CLIENT_ID and self.SPOTIFY_CLIENT_SECRET)

    @property
    def lastfm_configured(self) -> bool:
        """Return whether Last.fm credentials are configured without exposing them."""
        return bool(self.LASTFM_API_KEY)

    @property
    def youtube_configured(self) -> bool:
        """Return whether YouTube Data API credentials are configured."""
        return bool(self.YOUTUBE_API_KEY)

    @property
    def soundcloud_configured(self) -> bool:
        """Return whether SoundCloud credentials are configured."""
        return bool(self.SOUNDCLOUD_CLIENT_ID and self.SOUNDCLOUD_CLIENT_SECRET)

    # ------------------------------------------------------------------
    # Legacy lower-case compatibility aliases.
    #
    # The V2 services were written before the V3.4 collector contract and use
    # lower-case setting access in several places. Keep these aliases so V3.4-A
    # does not regress the V2 evidence integrations that V3 will reuse.
    # ------------------------------------------------------------------
    @property
    def spotify_client_id(self) -> str | None:
        """Compatibility alias for the Spotify client id."""
        return self.SPOTIFY_CLIENT_ID

    @property
    def spotify_client_secret(self) -> str | None:
        """Compatibility alias for the Spotify client secret.

        This is only for internal service compatibility. Public endpoints must
        never serialize this value.
        """
        return self.SPOTIFY_CLIENT_SECRET

    @property
    def spotify_token_url(self) -> str:
        """Compatibility alias for the Spotify token endpoint."""
        return self.SPOTIFY_TOKEN_URL

    @property
    def spotify_api_base_url(self) -> str:
        """Compatibility alias for the Spotify API base URL."""
        return self.SPOTIFY_API_BASE_URL

    @property
    def spotify_default_market(self) -> str:
        """Compatibility alias for the default Spotify market."""
        return self.SPOTIFY_DEFAULT_MARKET

    @property
    def spotify_artist_search_limit(self) -> int:
        """Compatibility alias for Spotify artist search limit."""
        return self.SPOTIFY_ARTIST_SEARCH_LIMIT

    @property
    def spotify_top_track_limit(self) -> int:
        """Compatibility alias for Spotify top track limit."""
        return self.SPOTIFY_TOP_TRACK_LIMIT

    @property
    def spotify_release_limit(self) -> int:
        """Compatibility alias for Spotify release limit."""
        return self.SPOTIFY_RELEASE_LIMIT

    @property
    def lastfm_api_key(self) -> str | None:
        """Compatibility alias for the Last.fm API key."""
        return self.LASTFM_API_KEY

    @property
    def lastfm_api_base_url(self) -> str:
        """Compatibility alias for the Last.fm API base URL."""
        return self.LASTFM_API_BASE_URL

    @property
    def lastfm_top_track_limit(self) -> int:
        """Compatibility alias for Last.fm top track limit."""
        return self.LASTFM_TOP_TRACK_LIMIT

    @property
    def lastfm_user_agent(self) -> str:
        """Compatibility alias for Last.fm User-Agent."""
        return self.LASTFM_USER_AGENT


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance.

    Caching avoids reparsing `.env` on every import and keeps configuration
    predictable during local development and tests.
    """
    return Settings()


settings = get_settings()
