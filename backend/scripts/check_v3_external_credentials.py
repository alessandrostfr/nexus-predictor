"""Validate V3.4-B official API credential status without external calls."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.v3_external_api_probe_service import V3ExternalAPIProbeService  # noqa: E402


def main() -> int:
    """Print sanitized credential status for official V3.4-B API probes."""
    with SessionLocal() as db:
        payload = V3ExternalAPIProbeService(db).credential_status()

    print("Nexus Predictor V3.4-B official API credential validation")
    print("=" * 72)
    print(f"OK  block: {payload.block}")
    print(f"OK  secret_values_exposed: {payload.secret_values_exposed}")
    for source in payload.sources:
        marker = "OK " if source.configured_status == "configured" else "WARN"
        print(f"{marker} {source.source_key}: {source.configured_status}")
        for env_name, status in source.credential_status.items():
            print(f"    - {env_name}: {status}")
        print(f"    next_action: {source.next_action}")
    print("=" * 72)
    print("V3.4-B credential diagnostic completed without external calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
