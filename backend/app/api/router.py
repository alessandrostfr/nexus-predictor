"""Central API router.

All endpoint modules are included here so `main.py` only has to register one
router. V2.9 adds optimized timetable variants while keeping V1/V2 routes
stable and clearly separated from future official timetable imports.
"""

from fastapi import APIRouter

from app.api import (
    ingestion,
    artist_profiles,
    artists,
    database,
    editions,
    evidence,
    genres,
    health,
    historical_timetables,
    predictions,
    probable_timetables,
    optimized_timetables,
    room_risk,
    social_platforms,
    spotify,
    venue,
)

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
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion-v2"])
api_router.include_router(historical_timetables.router, prefix="/historical-timetables", tags=["historical-timetables-v2"])
api_router.include_router(probable_timetables.router, prefix="/probable-timetables", tags=["probable-timetables-v2"])
api_router.include_router(optimized_timetables.router, prefix="/optimized-timetables", tags=["optimized-timetables-v2"])
api_router.include_router(social_platforms.router, prefix="/social-platforms", tags=["social-platforms-v2"])