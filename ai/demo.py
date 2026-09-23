"""Run with python ai/demo.py from the project root."""

import json

if __package__:
    from .core.baseline import calculate_baseline
    from .core.data_loader import load_checkins, load_sensor_readings
    from .core.drift_engine import analyze_drift
else:
    from core.baseline import calculate_baseline
    from core.data_loader import load_checkins, load_sensor_readings
    from core.drift_engine import analyze_drift


def main():
    checkins, sensors = load_checkins(), load_sensor_readings()
    baseline = calculate_baseline(checkins)
    stable = analyze_drift(checkins[:7], baseline, sensors)
    final = analyze_drift(checkins, baseline, sensors)
    print("--- PSYCHOSPACE DRIFT ENGINE ---\n\n" + baseline["user_id"] + "\n\nBASELINE")
    for label, field in (
        ("Sleep", "sleep_hours"), ("Mood", "mood"), ("Stress", "stress"),
        ("Fatigue", "fatigue"), ("Energy", "energy"), ("Social", "social_level"),
        ("Activity", "activity_minutes"),
    ):
        print(f"{label}: {baseline[field + '_avg']}")
    for label, result in (("STABLE PERIOD", stable), ("FINAL PERIOD", final)):
        print(f"\nANALYSIS — {label}")
        print(f"Drift score: {result['drift_score']}/100")
        print(f"Level: {result['level']}")
        print(f"Confidence: {result['confidence']}")
        print("Affected signals: " + json.dumps(result["affected_signals"], indent=2, ensure_ascii=True))
        print("Explanation: " + result["explanation"])
        print("Sensor context: " + json.dumps(result["sensor_context"], indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
