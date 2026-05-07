"""Central API router.

All endpoint modules are included here so `main.py` only has to register one
router. V2.1 adds the evidence router without changing existing V1-compatible
routes.
"""

from fastapi import APIRouter

from app.api import artist_profiles, artists, database, editions, evidence, genres, health, predictions, room_risk, spotify, venue

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(database.router, prefix="/database", tags=["database"])
api_router.include_router(editions.router, prefix="/editions", tags=["editions"])
api_router.include_router(artists.router, prefix="/artists", tags=["artists"])
api_router.include_router(artist_profiles.router, prefix="/artist-profiles", tags=["artist-profiles"])
api_router.include_router(venue.router, prefix="/venue", tags=["venue"])
api_router.include_router(genres.router, prefix="/genres", tags=["genres"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(room_risk.router, prefix="/room-risk", tags=["room-risk"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence-v2"])
api_router.include_router(spotify.router, prefix="/spotify", tags=["spotify-v2"])
