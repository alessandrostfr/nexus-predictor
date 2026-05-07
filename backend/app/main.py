"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.database_seed_service import ensure_database_ready


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the database connection and optional seed data on startup.

    V2 keeps schema management in Alembic. The application can still auto-create
    tables only when `AUTO_CREATE_DATABASE_SCHEMA=true`, which is useful for
    temporary SQLite checks but not the official PostgreSQL workflow.
    """
    with SessionLocal() as db:
        ensure_database_ready(db)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    fastapi_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API foundation for the Nexus Festival prediction dashboard.",
        lifespan=lifespan,
    )

    # CORS allows the current Vite frontend and the future Next.js frontend to
    # call the API during local development.
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(api_router, prefix="/api")

    return fastapi_app


app = create_app()
