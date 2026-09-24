from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_create_checkin_success():
    client = TestClient(app)
    existing = client.get("/api/checkins").json()
    used_dates = {item["checkin_date"] for item in existing}

    unique_date = None
    for offset in range(1, 366):
        candidate = (date.today() + timedelta(days=offset)).isoformat()
        if candidate not in used_dates:
            unique_date = candidate
            break

    if unique_date is None:
        pytest.fail("Aucune date libre disponible dans les 365 jours suivants pour ce test.")

    payload = {
        "astronaut_id": 1,
        "checkin_date": unique_date,
        "sleep_duration_hours": 7.5,
        "sleep_quality": 8,
        "fatigue": 3,
        "energy": 8,
        "stress": 4,
        "stress_source": "routine",
        "mood": 8,
        "motivation": 9,
        "concentration": 8,
        "unusual_difficulty": "none",
        "overall_state": 8,
        "compared_to_yesterday": "stable",
        "comment": "Bonne journée, récupération correcte."
    }

    response = client.post("/api/checkins", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["astronaut_id"] == 1
    assert data["checkin_date"] == unique_date
    assert data["overall_state"] == 8
    assert data["comment"] == "Bonne journée, récupération correcte."


def test_create_checkin_with_astronaut_names():
    client = TestClient(app)
    unique_date = (date.today() + timedelta(days=400)).isoformat()

    payload = {
        "astronaut_first_name": "Luna",
        "astronaut_last_name": "Martin",
        "checkin_date": unique_date,
        "sleep_duration_hours": 6.8,
        "sleep_quality": 7,
        "fatigue": 5,
        "energy": 7,
        "stress": 4,
        "stress_source": "routine",
        "mood": 8,
        "motivation": 9,
        "concentration": 7,
        "unusual_difficulty": "none",
        "overall_state": 7,
        "compared_to_yesterday": "stable",
        "comment": "Semaine équilibrée."
    }

    response = client.post("/api/checkins", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["astronaut_first_name"] == "Luna"
    assert data["astronaut_last_name"] == "Martin"


def test_list_checkins():
    client = TestClient(app)
    response = client.get("/api/checkins")

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)


def test_list_sensors_and_latest_readings():
    client = TestClient(app)
    sensors_response = client.get("/api/sensors")
    assert sensors_response.status_code == 200, sensors_response.text
    sensors = sensors_response.json()
    assert isinstance(sensors, list)
    if sensors:
        sensor_id = sensors[0]["id"]
        readings_response = client.get(f"/api/sensors/{sensor_id}/readings")
        assert readings_response.status_code == 200, readings_response.text
        payload = readings_response.json()
        assert isinstance(payload, list)
