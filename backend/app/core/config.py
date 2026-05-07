"""Application settings for the Nexus Predictor backend.

This module centralizes environment-based configuration so the FastAPI app,
database layer and external integrations can share the same settings object.
"""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or `.env`.

    Important: BACKEND_CORS_ORIGINS is intentionally stored as a plain string.
    This keeps local `.env` files simple and avoids pydantic-settings trying to
    parse comma-separated URLs as a JSON array during test collection.
    """

    # Basic application metadata.
    APP_NAME: str = "Nexus Predictor API"
    APP_VERSION: str = "0.8.0"
    ENVIRONMENT: str = "development"

    # Local SQLite database used by the MVP.
    DATABASE_URL: str = "sqlite:///./nexus_predictor.db"

    # Keep this as a comma-separated string in `.env`, for example:
    # BACKEND_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    # Local development convenience: seed the SQLite DB from JSON when needed.
    AUTO_SEED_DATABASE: bool = True

    # External enrichment remains opt-in so tests and local development are stable.
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
        """Return CORS origins as a clean list for FastAPI middleware.

        The project historically used comma-separated values. This parser also
        accepts a JSON array to be tolerant if a developer writes the setting in
        pydantic's complex-value style.
        """
        raw_origins = self.BACKEND_CORS_ORIGINS.strip()

        if not raw_origins:
            return []

        # Optional support for JSON array syntax:
        # BACKEND_CORS_ORIGINS=["http://127.0.0.1:5173", "http://localhost:5173"]
        if raw_origins.startswith("["):
            try:
                parsed_origins = json.loads(raw_origins)
                if isinstance(parsed_origins, list):
                    return [str(origin).strip() for origin in parsed_origins if str(origin).strip()]
            except json.JSONDecodeError:
                # Fall back to comma-separated parsing below.
                pass

        # Default and recommended local syntax: comma-separated URLs.
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance.

    Caching avoids reparsing `.env` on every import and keeps configuration
    predictable during local development and tests.
    """
    return Settings()


settings = get_settings()
