"""Seed the local SQLite database from editable JSON files.

Run it from `backend/` with the virtual environment active:

    python scripts/seed_database.py
"""


from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.services.database_seed_service import get_database_status, seed_database_from_json


def main() -> None:
    """Reset and seed SQLite from the current JSON dataset."""
    with SessionLocal() as db:
        result = seed_database_from_json(db, reset=True)
        status = get_database_status(db)

    print("Seed result:", result)
    print("Database status:", status)


if __name__ == "__main__":
    main()
