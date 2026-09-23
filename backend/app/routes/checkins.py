from fastapi import APIRouter, Request

from ..database import get_connection
from .measurements import Measurement, NonNegative, Score, TIME_ORDER, require_user

router = APIRouter(prefix="/api/checkins", tags=["checkins"])


class Checkin(Measurement):
    sleep_hours: NonNegative
    mood: Score
    stress: Score
    fatigue: Score
    energy: Score
    social_level: Score
    activity_minutes: NonNegative


@router.post("", status_code=201)
def create_checkin(checkin: Checkin, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, checkin.user_id)
        cursor = connection.execute(
            "INSERT INTO daily_checkins (user_id, timestamp, sleep_hours, mood, stress, "
            "fatigue, energy, social_level, activity_minutes) "
            "VALUES (:user_id, :timestamp, :sleep_hours, :mood, :stress, "
            ":fatigue, :energy, :social_level, :activity_minutes)",
            checkin.model_dump(),
        )
        identifier = cursor.lastrowid
    return {"success": True, "checkin_id": identifier}


@router.get("/{user_id}", response_model=list[Checkin])
def get_checkins(user_id: str, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, user_id)
        rows = connection.execute(
            "SELECT user_id, timestamp, sleep_hours, mood, stress, fatigue, energy, "
            "social_level, activity_minutes FROM daily_checkins "
            "WHERE user_id = ? ORDER BY " + TIME_ORDER,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]
