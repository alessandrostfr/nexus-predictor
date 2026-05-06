"""Initial scoring helpers.

The real demand and attendance model will be built in later blocks. This file is
kept now so the project has a clear place for prediction-related logic.
"""


def normalize_score(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a score into a safe range.

    Args:
        value: Raw score calculated by future scoring rules.
        minimum: Lowest allowed score.
        maximum: Highest allowed score.

    Returns:
        A score between `minimum` and `maximum`.
    """
    return max(minimum, min(maximum, value))
