"""Health-check endpoints used to verify that the API is running."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health_check() -> dict[str, object]:
    """Return a simple status payload for local validation and monitoring."""
    return {
        "success": True,
        "message": "Nexus Predictor API is running.",
        "data": {
            "status": "ok",
        },
    }
