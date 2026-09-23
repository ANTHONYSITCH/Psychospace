from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DailyCheckinCreate(BaseModel):
    astronaut_id: int
    checkin_date: date
    sleep_duration_hours: Optional[float] = None
    sleep_quality: Optional[int] = Field(default=None, ge=0, le=10)
    fatigue: Optional[int] = Field(default=None, ge=0, le=10)
    energy: Optional[int] = Field(default=None, ge=0, le=10)
    stress: Optional[int] = Field(default=None, ge=0, le=10)
    stress_source: Optional[str] = None
    mood: Optional[int] = Field(default=None, ge=0, le=10)
    motivation: Optional[int] = Field(default=None, ge=0, le=10)
    concentration: Optional[int] = Field(default=None, ge=0, le=10)
    unusual_difficulty: Optional[str] = None
    overall_state: Optional[int] = Field(default=None, ge=0, le=10)
    compared_to_yesterday: Optional[str] = None
    comment: Optional[str] = None


class DailyCheckinOut(DailyCheckinCreate):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AstronautOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class SensorReadingOut(BaseModel):
    id: int
    sensor_id: int
    recorded_at: datetime
    value: float
    quality_status: str

    model_config = ConfigDict(from_attributes=True)
