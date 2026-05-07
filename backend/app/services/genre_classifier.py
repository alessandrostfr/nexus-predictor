"""Compatibility import for the active genre classifier.

The old Block 4 service name is kept because scripts/tests/frontend imports may
still refer to `GenreClassifierService`. V2.5 routes and scripts now use the
multi-genre implementation underneath.
"""

from app.services.multi_genre_service import MultiGenreClassifierService


class GenreClassifierService(MultiGenreClassifierService):
    """Backward-compatible alias for the V2.5 multi-genre classifier."""

    pass
