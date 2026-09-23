"""Minimal SQLite context; no seed access or implicit engine calculation."""

import json

from ..routes.measurements import require_user

CHAT_LIMIT = 6


def order(column, descending=False, tie_breaker="rowid"):
    direction = " DESC" if descending else " ASC"
    return ", ".join(part + direction for part in (
        f"substr({column}, 1, 19)", f"CAST(substr({column}, 20) AS REAL)", tie_breaker))


def read_context(connection, user_id):
    """Materialize all rows; returned data holds no cursors or connections."""
    require_user(connection, user_id)
    profile = dict(connection.execute(
        "SELECT u.first_name, p.preferred_support, "
        "p.preferred_contact_time FROM users u "
        "LEFT JOIN profiles p ON u.user_id = p.user_id WHERE u.user_id = ?",
        (user_id,),
    ).fetchone())

    def recent(table, columns, timestamp, limit, tie_breaker="rowid"):
        return [dict(row) for row in connection.execute(
            f"SELECT {columns} FROM {table} WHERE user_id = ? "
            f"ORDER BY {order(timestamp, True, tie_breaker)} LIMIT ?", (user_id, limit))]

    baseline = recent("baselines", "sleep_hours_avg, mood_avg, stress_avg, "
                      "fatigue_avg, energy_avg, social_level_avg, activity_minutes_avg",
                      "calculated_at", 1)
    drift = recent("drift_events", "id, detected_at, level, drift_score, affected_signals, explanation",
                   "detected_at", 1, "id")
    return {
        "profile": profile,
        "baseline": baseline[0] if baseline else None,
        "current_drift": drift[0] if drift else None,
        "recent_checkins": list(reversed(recent("daily_checkins", "sleep_hours, mood, stress, fatigue, "
                                               "energy, social_level, activity_minutes", "timestamp", 3))),
        # V0.1: all entries in the user-managed vault are authorized.
        "memories": [dict(row) for row in connection.execute(
            "SELECT content FROM memories WHERE user_id = ? "
            "ORDER BY importance DESC, created_at DESC, id LIMIT 12", (user_id,))],
        "recent_chat": list(reversed(recent("chat_messages", "role, content", "timestamp", CHAT_LIMIT))),
    }


def format_context(data):
    """Build the structured context entirely in memory, after the read connection closes."""
    context = {**data}
    if data["current_drift"]:
        context["current_drift"] = {**data["current_drift"]}
        context["current_drift"]["affected_signals"] = json.loads(data["current_drift"]["affected_signals"] or "[]")
    return context


def build_context(connection, user_id):
    """Convenience for callers already managing a read-only connection."""
    return format_context(read_context(connection, user_id))
