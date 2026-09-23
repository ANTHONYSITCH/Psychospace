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


def test_list_checkins():
    client = TestClient(app)
    response = client.get("/api/checkins")

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
