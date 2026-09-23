"""Persisted API objects adapted from the unmodified deterministic engines."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException

from ai.core.baseline import calculate_baseline
from ai.core.data_loader import SIGNALS, parse_timestamp, validate_records
from ai.core.drift_engine import analyze_drift

from ..database import get_connection

BASELINE_COLUMNS = "user_id, calculated_at, " + ", ".join(s + "_avg" for s in SIGNALS) + ", observation_days"
CHECKIN_COLUMNS = "user_id, timestamp, " + ", ".join(SIGNALS)
EVENT_COLUMNS = "id, user_id, detected_at, level, drift_score, confidence, affected_signals, explanation, status"


def _require_user(connection, user_id):
    if not user_id.strip():
        raise HTTPException(400, "Identifiant utilisateur vide.")
    if connection.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone() is None:
        raise HTTPException(404, "Utilisateur introuvable.")


def _latest_baseline(connection, user_id):
    row = connection.execute(
        f"SELECT {BASELINE_COLUMNS} FROM baselines WHERE user_id = ? "
        "ORDER BY substr(calculated_at, 1, 19) DESC, "
        "CAST(substr(calculated_at, 20) AS REAL) DESC, id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _checkins(connection, user_id):
    return [dict(row) for row in connection.execute(
        f"SELECT {CHECKIN_COLUMNS} FROM daily_checkins WHERE user_id = ? "
        "ORDER BY substr(timestamp, 1, 19), CAST(substr(timestamp, 20) AS REAL), id",
        (user_id,),
    )]


def _recorded_at(*floors):
    """Logical UTC clock: stay after the data and existing future-dated fixtures."""
    current = datetime.now(timezone.utc)
    for stamp in floors:
        if stamp is not None:
            current = max(current, parse_timestamp(stamp) + timedelta(microseconds=1))
    return current.isoformat(timespec="microseconds").replace("+00:00", "Z")


def get_baseline(database_path, user_id):
    with get_connection(database_path) as connection:
        _require_user(connection, user_id)
        baseline = _latest_baseline(connection, user_id)
    if baseline is None:
        raise HTTPException(404, "Aucune baseline enregistrée. Calculez-la d'abord.")
    return baseline


def calculate_and_save_baseline(database_path, user_id):
    with get_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_user(connection, user_id)
        checkins = _checkins(connection, user_id)
        try:
            result = calculate_baseline(checkins, observation_days=7)
        except ValueError as exc:
            raise HTTPException(400, f"Calcul impossible : {exc}") from exc
        previous = _latest_baseline(connection, user_id)
        result["calculated_at"] = _recorded_at(
            result["calculated_at"], previous["calculated_at"] if previous else None,
        )
        columns = [column.strip() for column in BASELINE_COLUMNS.split(",")]
        connection.execute(
            f"INSERT INTO baselines ({BASELINE_COLUMNS}) VALUES ({', '.join('?' for _ in columns)})",
            [result[column] for column in columns],
        )
    return result


def adapt_drift_result(result, detected_at):
    """Discard internal-only context rather than adding fields to the contract."""
    if result["level"] == "stable":
        return None
    return {
        "id": "DRIFT-" + str(uuid4()), "user_id": result["user_id"],
        "detected_at": detected_at,
        "level": {"mild": "low", "moderate": "moderate", "high": "high"}[result["level"]],
        "drift_score": round(result["drift_score"] / 100, 6),
        "confidence": result["confidence"],
        "affected_signals": list(result["affected_signals"]),
        "explanation": result["explanation"], "status": "open",
    }


def analyze_and_save_drift(database_path, user_id):
    with get_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_user(connection, user_id)
        baseline = _latest_baseline(connection, user_id)
        if baseline is None:
            raise HTTPException(400, "Baseline absente : calculez-la avant de demander une analyse.")
        checkins = _checkins(connection, user_id)
        sensors = [dict(row) for row in connection.execute(
            "SELECT user_id, sensor_type, value, unit, timestamp FROM sensor_readings "
            "WHERE user_id = ? ORDER BY timestamp, id", (user_id,),
        )]
        try:
            ordered = validate_records(checkins)
            days = baseline["observation_days"]
            if type(days) is not int or days < 1 or len(ordered) < days:
                raise ValueError("Jours de référence insuffisants pour la baseline enregistrée")
            # Stored calculated_at is an execution date; the engine expects the
            # reference data cutoff. In this prototype: first observation_days.
            engine_baseline = {**baseline, "calculated_at": ordered[days - 1]["timestamp"]}
            result = analyze_drift(ordered, engine_baseline, sensor_readings=sensors, recent_window=3)
        except ValueError as exc:
            raise HTTPException(400, f"Analyse impossible : {exc}") from exc
        previous = connection.execute(
            "SELECT detected_at FROM drift_events WHERE user_id = ? "
            "ORDER BY substr(detected_at, 1, 19) DESC, "
            "CAST(substr(detected_at, 20) AS REAL) DESC, id DESC LIMIT 1", (user_id,),
        ).fetchone()
        event = adapt_drift_result(result, _recorded_at(
            ordered[-1]["timestamp"], baseline["calculated_at"], previous[0] if previous else None,
        ))
        if event is not None:
            stored = {**event, "affected_signals": json.dumps(event["affected_signals"], ensure_ascii=False)}
            columns = [column.strip() for column in EVENT_COLUMNS.split(",")]
            connection.execute(
                f"INSERT INTO drift_events ({EVENT_COLUMNS}) VALUES ({', '.join('?' for _ in columns)})",
                [stored[column] for column in columns],
            )
    return event


def get_drift_history(database_path, user_id):
    with get_connection(database_path) as connection:
        _require_user(connection, user_id)
        events = [dict(row) for row in connection.execute(
            f"SELECT {EVENT_COLUMNS} FROM drift_events WHERE user_id = ? "
            "ORDER BY substr(detected_at, 1, 19), CAST(substr(detected_at, 20) AS REAL), id",
            (user_id,),
        )]
    for event in events:
        event["affected_signals"] = json.loads(event["affected_signals"])
    return events
