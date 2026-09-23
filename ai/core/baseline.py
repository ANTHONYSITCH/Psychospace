"""Compute the reference from the first observed days, never hardcoded means."""

from statistics import fmean

from .data_loader import SIGNALS, positive_days, validate_records


def calculate_baseline(checkins, observation_days=7):
    positive_days(observation_days, "observation_days")
    ordered = validate_records(checkins)
    if len(ordered) < observation_days:
        raise ValueError(f"Baseline : {observation_days} jours requis, {len(ordered)} disponibles")
    reference = ordered[:observation_days]
    return {
        "user_id": reference[0]["user_id"],
        # Deterministic data cutoff, not the wall-clock execution time.
        "calculated_at": reference[-1]["timestamp"],
        **{f"{signal}_avg": round(fmean(row[signal] for row in reference), 6) for signal in SIGNALS},
        "observation_days": observation_days,
    }
