"""Read-only JSON loading and validation, using only the standard library."""

import json
import math
import re
from datetime import datetime
from pathlib import Path

# core/ -> ai/ -> project root
SEEDS_PATH = Path(__file__).resolve().parents[2] / "database" / "seeds"
SIGNALS = (
    "sleep_hours", "mood", "stress", "fatigue", "energy",
    "social_level", "activity_minutes",
)
SCORES = SIGNALS[1:6]


def parse_timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
    ):
        raise ValueError("timestamp : date ISO 8601 UTC avec suffixe Z attendue")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"timestamp : date invalide {value!r}") from exc


def finite_number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} : nombre fini attendu")


def positive_days(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} : entier strictement positif attendu")


def validate_records(records, *, sensors=False):
    if not isinstance(records, list) or (not records and not sensors):
        raise ValueError("Un tableau de données est attendu, non vide pour les check-ins")
    expected = {"user_id", "timestamp"} | (
        {"sensor_type", "value", "unit"} if sensors else set(SIGNALS)
    )
    users, days = set(), set()
    for index, row in enumerate(records):
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError(f"Enregistrement {index} : champs incompatibles avec le contrat")
        if not isinstance(row["user_id"], str) or not row["user_id"].strip():
            raise ValueError(f"Enregistrement {index} : user_id vide ou invalide")
        users.add(row["user_id"])
        day = parse_timestamp(row["timestamp"]).date()
        if sensors:
            for field in ("sensor_type", "unit"):
                if not isinstance(row[field], str) or not row[field].strip():
                    raise ValueError(f"{field} : chaîne non vide attendue")
            finite_number(row["value"], "value")
            expected_unit = {"heart_rate": "bpm", "spo2": "%", "movement": "m/s²"}.get(row["sensor_type"])
            if expected_unit and row["unit"] != expected_unit:
                raise ValueError(f"Unité incompatible pour {row['sensor_type']}")
        else:
            if day in days:
                raise ValueError(f"Plusieurs check-ins pour le jour {day} : agrégation à définir")
            days.add(day)
            for field in SIGNALS:
                finite_number(row[field], field)
                if field in SCORES:
                    if type(row[field]) is not int or not 1 <= row[field] <= 10:
                        raise ValueError(f"{field} : entier de 1 à 10 attendu")
                elif row[field] < 0:
                    raise ValueError(f"{field} : durée négative")
    if len(users) > 1:
        raise ValueError("Les données doivent concerner un seul user_id")
    return sorted(records, key=lambda row: parse_timestamp(row["timestamp"]))


def _load(path, *, sensors=False):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Impossible de lire le fichier JSON {path}: {exc}") from exc
    return validate_records(payload, sensors=sensors)


def load_checkins(path=None):
    return _load(path if path is not None else SEEDS_PATH / "astro-001-checkins.json")


def load_sensor_readings(path=None):
    return _load(path if path is not None else SEEDS_PATH / "astro-001-sensors.json", sensors=True)
