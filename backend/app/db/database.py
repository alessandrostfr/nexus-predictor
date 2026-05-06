"""Database connection foundation.

SQLite is used in the first MVP because it is fast to start, requires no server,
and is enough for a local research dashboard. The same SQLAlchemy structure can
later point to PostgreSQL if the project grows.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# SQLite needs `check_same_thread=False` when used by FastAPI in local dev.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it after the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
