"""Application settings for the Nexus Predictor backend.

This module centralizes environment-based configuration so the FastAPI app,
database layer and external integrations can share the same settings object.
Keeping every setting declared here prevents runtime AttributeError issues when
services read configuration values during tests or local development.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or `.env`.

    Defaults are safe for local development. Private API keys are optional and
    external enrichment remains disabled unless explicitly enabled.
    """

    # Application metadata used by FastAPI and health endpoints.
    APP_NAME: str = "Nexus Predictor API"
    APP_VERSION: str = "0.4.0"
    ENVIRONMENT: str = "development"

    # Local database configuration. SQLite is enough for the MVP and can later
    # be replaced by PostgreSQL by changing only this URL.
    DATABASE_URL: str = "sqlite:///./nexus_predictor.db"

    # When true, the API creates tables and seeds SQLite from the editable JSON
    # dataset automatically if the database is empty.
    AUTO_SEED_DATABASE: bool = True

    # Comma-separated origins allowed to call the API during local development.
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    # Artist enrichment settings. External calls are disabled by default so
    # tests and local validation do not depend on internet access or secrets.
    ENABLE_EXTERNAL_ARTIST_ENRICHMENT: bool = False
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    LASTFM_API_KEY: str = ""
    MUSICBRAINZ_CONTACT_EMAIL: str = ""

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


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance.

    Caching avoids reparsing `.env` on every import and keeps configuration
    predictable during local development and tests.
    """
    return Settings()


settings = get_settings()
