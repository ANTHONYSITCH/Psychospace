"""SQLite connections and non-destructive schema initialization."""

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from .config import SCHEMA_PATH, get_database_path


@contextmanager
def get_connection(database_path: Path | None = None):
    path = database_path if database_path is not None else get_database_path()
    with closing(sqlite3.connect(path, timeout=30)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection


def _schema_objects(connection):
    return {
        (row[0], row[1]): row[2]
        for row in connection.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL"
        )
    }


def initialize_database(database_path: Path | None = None) -> None:
    path = database_path if database_path is not None else get_database_path()
    schema = SCHEMA_PATH.read_text(encoding="utf-8-sig")
    # Execute the real schema in memory to establish the expected structure.
    with closing(sqlite3.connect(":memory:")) as reference:
        reference.executescript(schema)
        expected = _schema_objects(reference)

    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as connection:
        current = _schema_objects(connection)
        if not current:
            # The official script owns BEGIN/COMMIT; do not wrap it in BEGIN.
            connection.executescript(schema)
        elif current != expected:
            raise RuntimeError(
                "Le schéma SQLite existant est incomplet ou différent du schéma "
                "officiel. Aucune migration automatique ni suppression effectuée."
            )
