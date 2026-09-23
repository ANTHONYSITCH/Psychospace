from fastapi import APIRouter, Request
from pydantic import model_validator

from ..database import get_connection
from .measurements import Measurement, NonBlank, TIME_ORDER, require_user

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class SensorReading(Measurement):
    sensor_type: NonBlank
    value: float
    unit: NonBlank

    @model_validator(mode="after")
    def check_known_unit(self):
        expected = {"heart_rate": "bpm", "spo2": "%", "movement": "m/s²"}.get(self.sensor_type)
        if expected is not None and self.unit != expected:
            raise ValueError(f"Unité attendue pour {self.sensor_type} : {expected}")
        return self


@router.post("", status_code=201)
def create_sensor(sensor: SensorReading, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, sensor.user_id)
        cursor = connection.execute(
            "INSERT INTO sensor_readings (user_id, sensor_type, value, unit, timestamp) "
            "VALUES (:user_id, :sensor_type, :value, :unit, :timestamp)",
            sensor.model_dump(),
        )
        identifier = cursor.lastrowid
    return {"success": True, "sensor_reading_id": identifier}


@router.get("/{user_id}", response_model=list[SensorReading])
def get_sensors(user_id: str, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, user_id)
        rows = connection.execute(
            "SELECT user_id, sensor_type, value, unit, timestamp FROM sensor_readings "
            "WHERE user_id = ? ORDER BY " + TIME_ORDER,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]
