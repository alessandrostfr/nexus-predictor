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
    APP_VERSION: str = "0.3.0"
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"
    DATABASE_URL: str = "sqlite:///./nexus_predictor.db"
    AUTO_SEED_DATABASE: bool = True

    # Block 3 external artist enrichment. External calls are disabled by default
    # so local tests and normal API browsing never depend on internet access.
    ENABLE_EXTERNAL_ARTIST_ENRICHMENT: bool = False
    EXTERNAL_API_TIMEOUT_SECONDS: float = 10.0

    # Spotify uses the Client Credentials flow. These values must stay in `.env`.
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""

    # Last.fm requires an API key for artist info and top tracks.
    LASTFM_API_KEY: str = ""

    # MusicBrainz requires a descriptive User-Agent. A contact email is strongly
    # recommended when doing real requests from a local development machine.
    MUSICBRAINZ_APP_NAME: str = "NexusPredictor"
    MUSICBRAINZ_CONTACT_EMAIL: str = ""

    # The `.env` file lives inside the backend folder and is ignored by Git.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a clean list for FastAPI middleware."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def external_timeout(self) -> float:
        """Return a safe positive timeout for external APIs."""
        return max(3.0, float(self.EXTERNAL_API_TIMEOUT_SECONDS))

    @property
    def musicbrainz_user_agent(self) -> str:
        """Build the MusicBrainz User-Agent used by the metadata client."""
        contact = f" ({self.MUSICBRAINZ_CONTACT_EMAIL})" if self.MUSICBRAINZ_CONTACT_EMAIL else ""
        return f"{self.MUSICBRAINZ_APP_NAME}/0.3.0{contact}"


@lru_cache
def get_settings() -> Settings:
    """Cache settings so they are created only once per process."""
    return Settings()


settings = get_settings()
