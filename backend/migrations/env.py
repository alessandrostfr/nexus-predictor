"""Alembic environment for Nexus Predictor V2.

The project now uses PostgreSQL as the main database for V2. Alembic reads the
database URL from the same settings object used by FastAPI so local development,
tests and future deployments share a single configuration source.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Import path bootstrap
# ---------------------------------------------------------------------------
# Alembic executes this file from the migrations folder. We add the backend
# directory to sys.path so imports like "from app.core.config import settings"
# work consistently from PowerShell, bash and CI.
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.db import models  # noqa: F401,E402  # Imported so SQLAlchemy registers metadata.

# Alembic Config object, populated from backend/alembic.ini.
config = context.config

# Configure Python logging if the .ini file contains logging sections.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic to the same DB URL that the app uses.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Metadata used by Alembic autogenerate in future V2 blocks.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without opening a live database connection."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live SQLAlchemy connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
