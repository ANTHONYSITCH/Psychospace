import os
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyCheckin
from app.schemas import DailyCheckinCreate, DailyCheckinOut

app = FastAPI(title="Psychospace API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/api/checkins", response_model=DailyCheckinOut)
def create_checkin(payload: DailyCheckinCreate, db: Session = Depends(get_db)):
    checkin = DailyCheckin(
        astronaut_id=payload.astronaut_id,
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
        return checkin
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un check-in existe déjà pour cet astronaute à cette date."
        )


@app.get("/api/checkins", response_model=List[DailyCheckinOut])
def list_checkins(db: Session = Depends(get_db)):
    return db.query(DailyCheckin).order_by(DailyCheckin.checkin_date.desc()).all()


@app.get("/api/checkins/{checkin_id}", response_model=DailyCheckinOut)
def get_checkin(checkin_id: int, db: Session = Depends(get_db)):
    checkin = db.query(DailyCheckin).filter(DailyCheckin.id == checkin_id).first()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkin not found")
    return checkin
