"""Interpretable scoring helpers for Nexus Predictor.

Block 5 intentionally uses transparent rules instead of a black-box model. The
historical dataset is still small, so deterministic scoring is more useful and
honest than pretending we have enough labelled crowd data for a trained model.
"""

from dataclasses import dataclass

from app.schemas.prediction import PredictionFactor


@dataclass(frozen=True)
class ScoreBand:
    """Readable label for a numeric score range."""

    minimum: float
    label: str


# Weights are intentionally explicit because they are part of the prediction
# explanation shown to the user and can be tuned later from manual validation.
GENRE_STRENGTH_WEIGHTS: dict[str, float] = {
    "Rawstyle": 16.0,
    "Xtra Raw": 17.0,
    "Uptempo Hardcore": 16.0,
    "Hardcore": 15.0,
    "Frenchcore": 15.0,
    "Industrial Hardcore": 13.0,
    "Classic / Legacy Hardstyle": 18.0,
    "Euphoric Hardstyle": 14.0,
    "Happy Hardcore": 12.0,
    "Freestyle / Hard Dance": 9.0,
    "Hard Techno / Hard Dance": 8.0,
    "Mainstage Hard Dance": 12.0,
    "Terror / Speedcore": 10.0,
    "MC / Host": 2.0,
    "Unknown": 5.0,
}

# Manual hype is separate from genre and historical appearances. These values
# reflect strong expected demand from iconic projects or highly visible names in
# the 2026 context, while keeping the model editable and easy to audit.
MANUAL_HYPE_WEIGHTS: dict[str, float] = {
    "project-one": 32.0,
    "angerfist": 22.0,
    "sub-zero-project": 21.0,
    "showtek": 20.0,
    "wildstylez": 18.0,
    "brennan-heart": 17.0,
    "da-tweekaz": 16.0,
    "radical-redemption": 16.0,
    "phuture-noize": 15.0,
    "dual-damage": 15.0,
    "lil-texas": 15.0,
    "gpf": 14.0,
    "peacock": 14.0,
    "dr-peacock": 14.0,
    "korsakoff": 12.0,
    "re-style": 12.0,
    "the-dark-horror": 12.0,
    "n-vitral-bombsquad": 12.0,
    "spoontech-legacy": 11.0,
}

SPECIAL_PERFORMANCE_BONUS: dict[str, float] = {
    "b2b": 7.0,
    "versus": 7.0,
    "collaboration": 5.0,
    "special_show": 9.0,
    "live": 8.0,
    "duo_project": 10.0,
    "label_show": 8.0,
    "live_or_collective": 7.0,
    "solo": 0.0,
}


def normalize_score(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a score into a safe range."""
    return round(max(minimum, min(maximum, value)), 2)


def risk_from_score(score: float) -> str:
    """Translate a score into a user-facing crowd risk label."""
    if score >= 82:
        return "very_high"
    if score >= 68:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 32:
        return "low"
    return "very_low"


def confidence_from_score(score: float, *, unknown_genre: bool, prior_years: int) -> str:
    """Estimate confidence from score inputs, not from prediction quality claims."""
    if unknown_genre and prior_years == 0:
        return "low"
    if score >= 70 and prior_years >= 1:
        return "high"
    if prior_years >= 2:
        return "medium_high"
    return "medium"


def attendance_confidence(year_count: int, has_current_lineup: bool) -> str:
    """Return attendance confidence based on available historical inputs."""
    if year_count >= 4 and has_current_lineup:
        return "medium"
    if year_count >= 2:
        return "low_medium"
    return "low"


def factor(key: str, label: str, contribution: float, max_contribution: float, explanation: str) -> PredictionFactor:
    """Build one rounded prediction factor."""
    return PredictionFactor(
        key=key,
        label=label,
        contribution=round(contribution, 2),
        max_contribution=round(max_contribution, 2),
        explanation=explanation,
    )
