"""Central API router.

All endpoint modules are included here so `main.py` only has to register one
router. This keeps the backend structure tidy as the project grows.
"""

from fastapi import APIRouter

from app.api import editions, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(editions.router, prefix="/editions", tags=["editions"])
