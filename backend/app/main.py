"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    The factory pattern makes the app easier to test and keeps startup logic in
    one predictable place.
    """
    fastapi_app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="API foundation for the Nexus Festival prediction dashboard.",
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
