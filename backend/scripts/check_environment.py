"""Release helper to validate the local backend environment.

Run from backend/ with the virtual environment active:

    python scripts/check_environment.py

The script does not call external APIs and does not require private keys.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REQUIRED_MODULES = [
    "fastapi",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "httpx",
    "pandas",
    "sklearn",
]

REQUIRED_PATHS = [
    Path("app/data/editions"),
    Path("app/data/artists"),
    Path("app/data/venue/fabrik_rooms.json"),
    Path("app/data/timetables/2026.json"),
]


def check_python_version() -> list[str]:
    """Return warnings for unsupported Python versions."""
    warnings: list[str] = []
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        warnings.append(f"Python 3.11+ is recommended; current version is {major}.{minor}.")
    return warnings


def check_imports() -> list[str]:
    """Return missing dependency names."""
    missing: list[str] = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    return missing


def check_paths() -> list[str]:
    """Return missing project paths from the backend working directory."""
    return [str(path) for path in REQUIRED_PATHS if not path.exists()]


def main() -> None:
    """Print a release-friendly environment report."""
    print("Nexus Predictor backend environment check")
    print("Python executable:", sys.executable)
    print("Python version:", sys.version.split()[0])

    warnings = check_python_version()
    missing_modules = check_imports()
    missing_paths = check_paths()

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    if missing_modules:
        print("\nMissing Python packages:")
        for module_name in missing_modules:
            print(f"- {module_name}")
        print("\nRun: pip install -r requirements.txt")
        raise SystemExit(1)

    if missing_paths:
        print("\nMissing project files/folders:")
        for path in missing_paths:
            print(f"- {path}")
        raise SystemExit(1)

    print("\nEnvironment check completed successfully.")


if __name__ == "__main__":
    main()
