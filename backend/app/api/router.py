"""Central API router.

All endpoint modules are included here so `main.py` only has to register one
router. This keeps the backend structure tidy as the project grows.
"""

from fastapi import APIRouter

from app.api import artists, editions, health, venue

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(editions.router, prefix="/editions", tags=["editions"])
api_router.include_router(venue.router, prefix="/venue", tags=["venue"])
api_router.include_router(artists.router, prefix="/artists", tags=["artists"])
