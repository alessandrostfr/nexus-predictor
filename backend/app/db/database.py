"""Database connection foundation for Nexus Predictor V2.

V2 uses PostgreSQL as the default relational database and Alembic for schema
changes. SQLite remains technically supported for isolated local experiments by
changing `DATABASE_URL`, but the official V2 workflow is PostgreSQL + Docker.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def build_connect_args(database_url: str) -> dict[str, object]:
    """Return SQLAlchemy connect args depending on the selected database."""
    if database_url.startswith("sqlite"):
        # SQLite needs this flag when the same connection is used by FastAPI in
        # local development or tests.
        return {"check_same_thread": False}
    return {}


def create_database_engine() -> Engine:
    """Create the SQLAlchemy engine with safe defaults for long-running APIs."""
    return create_engine(
        settings.DATABASE_URL,
        connect_args=build_connect_args(settings.DATABASE_URL),
        pool_pre_ping=True,
    )


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def safe_database_url() -> str:
    """Expose the configured database URL without leaking credentials."""
    return settings.safe_database_url


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it after the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
