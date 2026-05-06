"""Application settings for the Nexus Predictor backend.

This module centralizes environment-based configuration so the FastAPI app,
database layer and future integrations can share the same settings object.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or `.env`.

    The default values are safe for local development. Sensitive API keys for
    Spotify, Last.fm or other services will be added in later roadmap blocks.
    """

    APP_NAME: str = "Nexus Predictor"
    DATABASE_URL: str = "sqlite:///./nexus_predictor.db"
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

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
