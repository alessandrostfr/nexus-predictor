"""Secret-safety helpers for V3 external ingestion."""

from __future__ import annotations

SECRET_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CLIENT_SECRET")
REDACTED = "***redacted***"


def is_secret_key(key: str) -> bool:
    """Return whether a key name probably contains secret material."""
    upper = key.upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def redact_value(key: str, value: object) -> object:
    """Redact a value when the key name indicates a secret."""
    if value in (None, ""):
        return value
    return REDACTED if is_secret_key(key) else value


def redact_payload(payload: dict[str, object]) -> dict[str, object]:
    """Return a shallow redacted payload safe for logs/API responses."""
    return {key: redact_value(key, value) for key, value in payload.items()}


def credential_status(env_values: dict[str, str | None], required_vars: tuple[str, ...]) -> dict[str, str]:
    """Return configured/missing status without exposing the secret values."""
    return {name: "configured" if env_values.get(name) else "missing" for name in required_vars}
