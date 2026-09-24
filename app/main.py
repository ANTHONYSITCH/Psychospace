import hashlib
import json
from datetime import date
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Astronaut, DailyCheckin, EventCertificate, Mission, Sensor, SensorReading
from app.schemas import (
    DailyCheckinCreate,
    DailyCheckinOut,
    EventCertificateOut,
    SensorOut,
    SensorReadingOut,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Psychospace API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):(\d+)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


def ensure_default_mission(db: Session) -> Mission:
    mission = db.query(Mission).order_by(Mission.id.asc()).first()
    if mission:
        return mission

    mission = Mission(
        name="Mission Alpha",
        description="Mission principale de démonstration Psychospace.",
        start_date=date.today(),
        status="active",
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def get_or_create_astronaut(db: Session, payload: DailyCheckinCreate) -> Astronaut:
    if payload.astronaut_id is not None:
        astronaut = db.query(Astronaut).filter(Astronaut.id == payload.astronaut_id).first()
        if astronaut:
            return astronaut
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Astronaute introuvable.")

    first_name = (payload.astronaut_first_name or "").strip()
    last_name = (payload.astronaut_last_name or "").strip()
    if not first_name or not last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le prénom et le nom de l'astronaute sont requis.",
        )

    astronaut = (
        db.query(Astronaut)
        .filter(Astronaut.first_name.ilike(first_name), Astronaut.last_name.ilike(last_name))
        .first()
    )
    if astronaut:
        return astronaut

    mission = ensure_default_mission(db)
    email_base = f"{first_name.lower()}.{last_name.lower()}@mission.local"
    email = email_base
    suffix = 1
    while db.query(Astronaut).filter(Astronaut.email == email).first():
        email = f"{first_name.lower()}.{last_name.lower()}{suffix}@mission.local"
        suffix += 1

    astronaut = Astronaut(
        mission_id=mission.id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash="generated-by-system",
        role="astronaut",
    )
    db.add(astronaut)
    db.commit()
    db.refresh(astronaut)
    return astronaut


def enrich_checkin_response(checkin: DailyCheckin):
    astronaut = checkin.astronaut
    payload = {**checkin.__dict__}
    payload.pop("_sa_instance_state", None)
    payload["astronaut_first_name"] = astronaut.first_name if astronaut else None
    payload["astronaut_last_name"] = astronaut.last_name if astronaut else None
    return payload


@app.post("/api/checkins", response_model=DailyCheckinOut)
def create_checkin(payload: DailyCheckinCreate, db: Session = Depends(get_db)):
    astronaut = get_or_create_astronaut(db, payload)

    checkin = DailyCheckin(
        astronaut_id=astronaut.id,
        checkin_date=payload.checkin_date,
        sleep_duration_hours=payload.sleep_duration_hours,
        sleep_quality=payload.sleep_quality,
        fatigue=payload.fatigue,
        energy=payload.energy,
        stress=payload.stress,
        stress_source=payload.stress_source,
        mood=payload.mood,
        motivation=payload.motivation,
        concentration=payload.concentration,
        unusual_difficulty=payload.unusual_difficulty,
        overall_state=payload.overall_state,
        compared_to_yesterday=payload.compared_to_yesterday,
        comment=payload.comment,
    )

    try:
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
        return enrich_checkin_response(checkin)
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un check-in existe déjà pour cet astronaute à cette date.",
        )


@app.get("/api/checkins", response_model=List[DailyCheckinOut])
def list_checkins(db: Session = Depends(get_db)):
    checkins = db.query(DailyCheckin).order_by(DailyCheckin.checkin_date.desc()).all()
    return [enrich_checkin_response(checkin) for checkin in checkins]


@app.get("/api/checkins/{checkin_id}", response_model=DailyCheckinOut)
def get_checkin(checkin_id: int, db: Session = Depends(get_db)):
    checkin = db.query(DailyCheckin).filter(DailyCheckin.id == checkin_id).first()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkin not found")
    return enrich_checkin_response(checkin)


@app.get("/api/astronauts")
def list_astronauts(db: Session = Depends(get_db)):
    astronauts = db.query(Astronaut).order_by(Astronaut.id.asc()).all()
    return [
        {
            "id": astronaut.id,
            "first_name": astronaut.first_name,
            "last_name": astronaut.last_name,
            "email": astronaut.email,
            "role": astronaut.role,
        }
        for astronaut in astronauts
    ]


@app.get("/api/sensors", response_model=List[SensorOut])
def list_sensors(db: Session = Depends(get_db)):
    sensors = db.query(Sensor).all()
    results = []
    for sensor in sensors:
        latest = (
            db.query(SensorReading)
            .filter(SensorReading.sensor_id == sensor.id)
            .order_by(SensorReading.recorded_at.desc())
            .first()
        )
        results.append(
            {
                "id": sensor.id,
                "mission_id": sensor.mission_id,
                "sensor_name": sensor.sensor_name,
                "sensor_type": sensor.sensor_type,
                "location": sensor.location,
                "unit": sensor.unit,
                "latest_value": float(latest.value) if latest else None,
                "quality_status": latest.quality_status if latest else None,
                "last_recorded_at": latest.recorded_at if latest else None,
            }
        )
    return results


@app.get("/api/sensors/{sensor_id}/readings", response_model=List[SensorReadingOut])
def get_sensor_readings(sensor_id: int, db: Session = Depends(get_db)):
    return (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.recorded_at.asc())
        .all()
    )


@app.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    latest_checkin = db.query(DailyCheckin).order_by(DailyCheckin.checkin_date.desc()).first()
    sensors = db.query(Sensor).all()
    sensor_points = []
    for sensor in sensors:
        latest = (
            db.query(SensorReading)
            .filter(SensorReading.sensor_id == sensor.id)
            .order_by(SensorReading.recorded_at.desc())
            .first()
        )
        if latest:
            sensor_points.append(
                {
                    "sensor_name": sensor.sensor_name,
                    "sensor_type": sensor.sensor_type,
                    "value": float(latest.value),
                    "unit": sensor.unit,
                    "quality_status": latest.quality_status,
                    "recorded_at": latest.recorded_at.isoformat() if latest.recorded_at else None,
                }
            )

    return {
        "latest_checkin": enrich_checkin_response(latest_checkin) if latest_checkin else None,
        "sensor_points": sensor_points,
    }


@app.get("/api/events/certify", response_model=List[EventCertificateOut])
def list_certificates(db: Session = Depends(get_db)):
    return db.query(EventCertificate).order_by(EventCertificate.id.desc()).all()


@app.post("/api/events/certify", response_model=EventCertificateOut)
def certify_event(payload: Dict[str, Any], db: Session = Depends(get_db)):
    event_type = str(payload.get("event_type", "event"))
    event_id = str(payload.get("event_id", "manual"))
    actor_name = payload.get("actor_name")
    event_data = payload.get("event_data", {})

    previous = db.query(EventCertificate).order_by(EventCertificate.id.desc()).first()
    previous_hash = previous.current_hash if previous else "GENESIS"
    encoded = json.dumps(
        {
            "event_type": event_type,
            "event_id": event_id,
            "actor_name": actor_name,
            "event_data": event_data,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
    )
    current_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    certificate = EventCertificate(
        event_type=event_type,
        event_id=event_id,
        actor_name=actor_name,
        previous_hash=previous_hash,
        current_hash=current_hash,
        event_payload=json.dumps(event_data, sort_keys=True),
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate
