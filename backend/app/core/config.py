"""Application settings for the Nexus Predictor backend.

V2 moves the project from a SQLite-first MVP into a PostgreSQL/Alembic setup.
All settings stay environment-driven so local development, tests and future
pipeline workers can share the same configuration contract.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or `.env`.

    Defaults are development-friendly and intentionally keep external enrichment
    disabled until the matching V2 roadmap blocks implement each source.
    """

    APP_NAME: str = "Nexus Predictor"
    APP_VERSION: str = "2.0.0-foundations"
    ENVIRONMENT: str = "development"

    # PostgreSQL is the default database for V2. SQLite remains supported for
    # isolated experiments by overriding DATABASE_URL in `.env`.
    DATABASE_URL: str = "postgresql+psycopg://nexus:nexus@localhost:5432/nexus_predictor"

    # V2 should rely on Alembic migrations by default. Keeping this switch makes
    # temporary SQLite smoke checks possible without changing application code.
    AUTO_CREATE_DATABASE_SCHEMA: bool = False
    AUTO_SEED_DATABASE: bool = True

    BACKEND_CORS_ORIGINS: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:3000,http://localhost:3000"
    )

    ENABLE_EXTERNAL_ARTIST_ENRICHMENT: bool = False
    EXTERNAL_REQUEST_TIMEOUT_SECONDS: float = 20.0
    MUSICBRAINZ_CONTACT_EMAIL: str | None = None

    # Reserved for V2.2. They are defined here now so the settings contract is
    # stable before the real Spotify enrichment block starts.
    SPOTIFY_CLIENT_ID: str | None = None
    SPOTIFY_CLIENT_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a clean list for FastAPI middleware."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def database_backend(self) -> str:
        """Return a simple database backend label used by diagnostics."""
        if self.DATABASE_URL.startswith("sqlite"):
            return "sqlite"
        if self.DATABASE_URL.startswith("postgresql"):
            return "postgresql"
        return "unknown"

    @property
    def external_timeout(self) -> float:
        """HTTP timeout used by enrichment services."""
        return self.EXTERNAL_REQUEST_TIMEOUT_SECONDS

    @property
    def musicbrainz_user_agent(self) -> str:
        """Return a respectful MusicBrainz User-Agent string."""
        contact = self.MUSICBRAINZ_CONTACT_EMAIL or "local-development@example.com"
        return f"{self.APP_NAME}/{self.APP_VERSION} ({contact})"

    @property
    def safe_database_url(self) -> str:
        """Return DATABASE_URL with the password hidden for logs and API status."""
        try:
            return make_url(self.DATABASE_URL).render_as_string(hide_password=True)
        except Exception:
            # Keep diagnostics resilient even if a developer is editing the URL.
            return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
