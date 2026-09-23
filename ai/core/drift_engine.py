"""Deterministic analysis context, not a persisted drift-event API object."""

from collections import defaultdict
from datetime import timedelta
from statistics import fmean

from .data_loader import (
    SCORES, SIGNALS, finite_number, parse_timestamp, positive_days, validate_records,
)

WEIGHTS = dict(zip(SIGNALS, (0.15, 0.15, 0.15, 0.15, 0.10, 0.15, 0.15)))
INCREASE = {"stress", "fatigue"}
LABELS = {
    "sleep_hours": "Sleep duration", "mood": "Mood", "stress": "Reported stress",
    "fatigue": "Fatigue", "energy": "Energy", "social_level": "Social interaction",
    "activity_minutes": "Physical activity",
}


def classify_score(score):
    finite_number(score, "drift_score")
    if not 0 <= score <= 100:
        raise ValueError("drift_score doit être entre 0 et 100")
    if score < 20:
        return "stable"
    if score < 40:
        return "mild"
    if score < 60:
        return "moderate"
    return "high"


def _validate_baseline(baseline, user_id):
    fields = {"user_id", "calculated_at", "observation_days"} | {f"{s}_avg" for s in SIGNALS}
    if not isinstance(baseline, dict) or set(baseline) != fields:
        raise ValueError("Baseline : champs incompatibles avec le contrat")
    if baseline["user_id"] != user_id:
        raise ValueError("La baseline et les check-ins doivent partager le même user_id")
    positive_days(baseline["observation_days"], "observation_days")
    parse_timestamp(baseline["calculated_at"])
    for signal in SIGNALS:
        value = baseline[f"{signal}_avg"]
        finite_number(value, signal)
        if (signal in SCORES and not 1 <= value <= 10) or value < 0:
            raise ValueError(f"Baseline : moyenne invalide pour {signal}")


def _severity(signal, reference, recent):
    change = recent - reference
    adverse = change if signal in INCREASE else -change
    scale = 3.0
    if signal in ("sleep_hours", "activity_minutes"):
        scale = reference * (0.25 if signal == "sleep_hours" else 0.5)
    # With nonnegative durations, a zero reference cannot decrease further.
    return min(1.0, max(0.0, adverse / scale)) if scale else 0.0


def _sensor_context(sensors, checkins, baseline, recent, activity_decreased):
    if not sensors:
        return {}
    user_id = checkins[0]["user_id"]
    if sensors[0]["user_id"] != user_id:
        raise ValueError("Les capteurs et les check-ins doivent partager le même user_id")
    cutoff = parse_timestamp(checkins[-1]["timestamp"])
    recent_days = {parse_timestamp(row["timestamp"]).date() for row in recent}
    baseline_cutoff = parse_timestamp(baseline["calculated_at"])
    reference_rows = [row for row in checkins if parse_timestamp(row["timestamp"]) <= baseline_cutoff]
    # No invented reference if the original baseline days are not supplied.
    reference_days = set()
    if len(reference_rows) == baseline["observation_days"]:
        reference_days = {parse_timestamp(row["timestamp"]).date() for row in reference_rows}

    context = {}
    for sensor_type in ("heart_rate", "spo2", "movement"):
        selected = [r for r in sensors if r["sensor_type"] == sensor_type
                    and parse_timestamp(r["timestamp"]) <= cutoff]
        daily = defaultdict(list)
        for row in selected:
            daily[parse_timestamp(row["timestamp"]).date()].append(row["value"])
        current = [fmean(values) for day, values in daily.items() if day in recent_days]
        if not current:
            continue
        item = {
            "unit": selected[0]["unit"], "recent_mean": round(fmean(current), 6),
            "days_observed": len(current),
            "reading_count": sum(len(v) for day, v in daily.items() if day in recent_days),
            "affects_score": False,
        }
        if sensor_type == "movement":
            reference = [fmean(values) for day, values in daily.items() if day in reference_days]
            reference_mean = fmean(reference) if len(reference) == baseline["observation_days"] else None
            confirmed = None if reference_mean is None else activity_decreased and fmean(current) < reference_mean
            item.update({
                "baseline_mean": round(reference_mean, 6) if reference_mean is not None else None,
                "confirms_activity_decrease": confirmed,
                "note": (
                    "Movement and reported activity both decreased compared with their reference."
                    if confirmed else "No confirmation of lower activity from the available movement data."
                ),
            })
        context[sensor_type] = item
    return context


def analyze_drift(checkins, baseline, sensor_readings=None, recent_window=3):
    positive_days(recent_window, "recent_window")
    ordered = validate_records(checkins)
    _validate_baseline(baseline, ordered[0]["user_id"])
    cutoff = parse_timestamp(ordered[-1]["timestamp"])
    if parse_timestamp(baseline["calculated_at"]) > cutoff:
        raise ValueError("La baseline utilise des données postérieures à la période analysée")
    first_day = cutoff.date() - timedelta(days=recent_window - 1)
    recent = [row for row in ordered if parse_timestamp(row["timestamp"]).date() >= first_day]
    sensors = validate_records(sensor_readings, sensors=True) if sensor_readings is not None else []
    affected, severities, recent_means = {}, {}, {}
    for signal in SIGNALS:
        reference = baseline[f"{signal}_avg"]
        mean = fmean(row[signal] for row in recent)
        recent_means[signal] = mean
        severity = _severity(signal, reference, mean)
        severities[signal] = severity
        if severity >= 0.25:
            change = mean - reference
            affected[signal] = {
                "baseline": reference, "recent": round(mean, 6),
                "change": round(change, 6), "severity": round(severity, 6),
                "direction": "increase" if signal in INCREASE else "decrease",
                "persistence_days": sum(
                    (row[signal] > reference if signal in INCREASE else row[signal] < reference)
                    for row in recent
                ),
            }
            if signal in ("sleep_hours", "activity_minutes"):
                affected[signal]["change_percent"] = round(change / reference * 100, 6) if reference else None

    score = round(min(100.0, max(0.0, sum(severities[s] * WEIGHTS[s] for s in SIGNALS) * 100)), 2)
    explanation = " ".join(
        f"{LABELS[s]} {'increased' if detail['direction'] == 'increase' else 'decreased'} "
        f"from a personal reference of {detail['baseline']:.2f} to a recent mean of {detail['recent']:.2f}; "
        f"{detail['persistence_days']}/{len(recent)} observed days were in this direction."
        for s, detail in affected.items()
    ) or "No signal reached the affected-signal threshold in the recent observation window."
    context = _sensor_context(
        sensors, ordered, baseline, recent,
        recent_means["activity_minutes"] < baseline["activity_minutes_avg"],
    )
    return {
        "user_id": ordered[0]["user_id"], "drift_score": score,
        "level": classify_score(score),
        "confidence": round(len(recent) / recent_window * min(baseline["observation_days"] / 7, 1), 6),
        "recent_window_days": len(recent), "affected_signals": affected,
        "sensor_context": context, "explanation": explanation,
    }
