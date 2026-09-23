"""Paths are independent of the process working directory."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
SEEDS_PATH = PROJECT_ROOT / "database" / "seeds"


def get_database_path() -> Path:
    """A simple path override; DATABASE_URL parsing is deferred."""
    path = Path(os.environ.get("PSYCHOSPACE_DB_PATH", "database/psychospace.db"))
    return path if path.is_absolute() else PROJECT_ROOT / path
