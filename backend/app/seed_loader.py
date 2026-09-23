"""Import the shared fixture once, atomically, into an empty database."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import SEEDS_PATH
from .database import get_connection

# SQL identifiers come only from these fixed definitions, never from input.
IMPORTS = (
    ("checkins", "daily_checkins", "user_id timestamp sleep_hours mood stress fatigue energy social_level activity_minutes"),
    ("sensors", "sensor_readings", "user_id sensor_type value unit timestamp"),
    ("memories", "memories", "id user_id category content importance source created_at"),
    ("baseline", "baselines", "user_id calculated_at sleep_hours_avg mood_avg stress_avg fatigue_avg energy_avg social_level_avg activity_minutes_avg observation_days"),
    ("drift-events", "drift_events", "id user_id detected_at level drift_score confidence affected_signals explanation status"),
    ("interventions", "interventions", "id user_id drift_event_id created_at type message accepted completed"),
)


def _read_seed(directory: Path, name: str):
    return json.loads((directory / f"astro-001-{name}.json").read_text(encoding="utf-8-sig"))


def load_seeds(database_path: Path | None = None, seeds_path: Path = SEEDS_PATH) -> bool:
    with get_connection(database_path) as connection:
        # Serialize the empty-database check and all inserts.
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return False

        profile = _read_seed(seeds_path, "profile")
        connection.execute(
            "INSERT INTO users (user_id, first_name, age, mission_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (profile["user_id"], profile["first_name"], profile["age"],
             profile["mission_id"], datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")),
        )
        connection.execute(
            "INSERT INTO profiles (user_id, normal_sleep_hours, preferred_support, "
            "preferred_contact_time, interests) VALUES (?, ?, ?, ?, ?)",
            (profile["user_id"], profile["normal_sleep_hours"], profile["preferred_support"],
             profile["preferred_contact_time"], json.dumps(profile["interests"], ensure_ascii=False)),
        )
        for filename, table, column_names in IMPORTS:
            payload = _read_seed(seeds_path, filename)
            rows = [payload] if filename == "baseline" else payload
            columns = column_names.split()
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})"
            for row in rows:
                if set(row) != set(columns) or row["user_id"] != profile["user_id"]:
                    raise ValueError(f"Seed incompatible : {filename}")
                values = [
                    json.dumps(row[column], ensure_ascii=False)
                    if column == "affected_signals" else row[column]
                    for column in columns
                ]
                connection.execute(query, values)
        return True
