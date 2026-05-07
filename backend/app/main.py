"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.database_seed_service import create_database_schema, ensure_database_ready
from app.services.evidence_seed_service import ensure_v2_evidence_ready


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare local database tables, V1 seed data and V2 evidence data."""
    create_database_schema()
    with SessionLocal() as db:
        ensure_database_ready(db)
        ensure_v2_evidence_ready(db)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    The factory pattern makes the app easier to test and keeps startup logic in
    one predictable place.
    """
    fastapi_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API foundation for the Nexus Festival prediction dashboard.",
        lifespan=lifespan,
    )

    # CORS allows the React frontend to call the API during local development.
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
