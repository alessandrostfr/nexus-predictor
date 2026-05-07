"""Validate the Nexus Predictor V2 foundations setup.

This script is intentionally small and explicit because it is used as a local
sanity check after applying Block V2.0. It verifies that:

- The backend package can be imported correctly.
- V2 settings are available.
- PostgreSQL is reachable through SQLAlchemy.
- Alembic configuration and migration folders exist.
- The V2 pipeline package is present.

Run from the backend folder:

    python scripts/check_v2_foundations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

# ---------------------------------------------------------------------------
# Import path bootstrap
# ---------------------------------------------------------------------------
# When this file is executed as "python scripts/check_v2_foundations.py",
# Python places "backend/scripts" in sys.path, not "backend".
# We add "backend" manually so imports like "from app.core.config import settings"
# work consistently on Windows, macOS and Linux.
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.database import engine  # noqa: E402


def check_alembic_files() -> None:
    """Ensure Alembic files created in V2.0 exist."""
    alembic_ini = BACKEND_DIR / "alembic.ini"
    migrations_dir = BACKEND_DIR / "migrations"
    env_file = migrations_dir / "env.py"
    template_file = migrations_dir / "script.py.mako"
    versions_dir = migrations_dir / "versions"

    missing_paths = [
        path
        for path in [alembic_ini, migrations_dir, env_file, template_file, versions_dir]
        if not path.exists()
    ]

    if missing_paths:
        formatted = "\n".join(f"- {path}" for path in missing_paths)
        raise RuntimeError(f"Missing Alembic files or folders:\n{formatted}")

    migration_files = list(versions_dir.glob("*.py"))
    if not migration_files:
        raise RuntimeError(
            "No Alembic migration files found in backend/migrations/versions."
        )

    print("Alembic files OK")


def check_pipeline_package() -> None:
    """Ensure the V2 pipelines package exists."""
    pipelines_dir = BACKEND_DIR / "app" / "pipelines"
    init_file = pipelines_dir / "__init__.py"

    if not pipelines_dir.exists() or not init_file.exists():
        raise RuntimeError(
            "Missing app/pipelines package. "
            "Block V2.0 should create backend/app/pipelines/__init__.py"
        )

    print("Pipeline package OK")


def check_settings() -> None:
    """Print and validate the most important V2 settings."""
    print("Settings OK")
    print(f"App name: {settings.APP_NAME}")
    print(f"App version: {settings.APP_VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database URL: {settings.DATABASE_URL}")


def check_database_connection() -> None:
    """Open a real SQLAlchemy connection against PostgreSQL."""
    with engine.connect() as connection:
        database_version = connection.execute(text("SELECT version();")).scalar_one()

    print("PostgreSQL connection OK")
    print(f"Database version: {database_version}")


def main() -> None:
    """Run all V2 foundation checks."""
    print("Nexus Predictor V2 foundations check")

    check_settings()
    check_alembic_files()
    check_pipeline_package()
    check_database_connection()

    print("V2 foundations check completed successfully.")


if __name__ == "__main__":
    main()
