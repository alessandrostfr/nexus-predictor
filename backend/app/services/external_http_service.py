"""Small HTTP helpers shared by external enrichment clients."""

from typing import Any

import httpx

from app.core.config import settings


class ExternalServiceError(RuntimeError):
    """Raised when an external service call fails in a controlled way."""


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Perform a JSON HTTP request with consistent error handling.

    External enrichment should never crash the API. Higher-level services catch
    `ExternalServiceError` and convert it into profile warnings.
    """
    try:
        with httpx.Client(timeout=timeout or settings.external_timeout) as client:
            response = client.request(method, url, headers=headers, params=params, data=data)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise ExternalServiceError(str(exc)) from exc
    except ValueError as exc:
        raise ExternalServiceError("External service returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise ExternalServiceError("External service returned an unexpected payload.")
    return payload
