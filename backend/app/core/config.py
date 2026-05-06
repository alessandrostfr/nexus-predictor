"""Application configuration.

The settings object reads values from environment variables and from `.env` during
local development. Keeping all settings here avoids scattering configuration
throughout the project.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings loaded from the environment."""

    APP_NAME: str = "Nexus Predictor API"
    APP_ENV: str = "local"
    APP_VERSION: str = "0.2.0"
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"
    DATABASE_URL: str = "sqlite:///./nexus_predictor.db"
    AUTO_SEED_DATABASE: bool = True
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    LASTFM_API_KEY: str = ""
    MUSICBRAINZ_CONTACT_EMAIL: str = ""

    # The `.env` file lives inside the backend folder and is ignored by Git.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a clean list for FastAPI middleware."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cache settings so they are created only once per process."""
    return Settings()


settings = get_settings()
