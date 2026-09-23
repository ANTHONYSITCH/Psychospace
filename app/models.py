from sqlalchemy import Column, Date, Integer, Numeric, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(30), default="active")
    created_at = Column(TIMESTAMP, nullable=True)

    astronauts = relationship("Astronaut", back_populates="mission")


class Astronaut(Base):
    __tablename__ = "astronauts"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="astronaut")
    created_at = Column(TIMESTAMP, nullable=True)

    mission = relationship("Mission", back_populates="astronauts")
    checkins = relationship("DailyCheckin", back_populates="astronaut")


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    astronaut_id = Column(Integer, ForeignKey("astronauts.id"), nullable=False)
    checkin_date = Column(Date, nullable=False)
    sleep_duration_hours = Column(Numeric(4, 2), nullable=True)
    sleep_quality = Column(Integer, nullable=True)
    fatigue = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    stress = Column(Integer, nullable=True)
    stress_source = Column(Text, nullable=True)
    mood = Column(Integer, nullable=True)
    motivation = Column(Integer, nullable=True)
    concentration = Column(Integer, nullable=True)
    unusual_difficulty = Column(String(100), nullable=True)
    overall_state = Column(Integer, nullable=True)
    compared_to_yesterday = Column(String(50), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)

    astronaut = relationship("Astronaut", back_populates="checkins")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    sensor_name = Column(String(100), nullable=False)
    sensor_type = Column(String(50), nullable=False)
    location = Column(String(100), nullable=True)
    unit = Column(String(30), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    recorded_at = Column(TIMESTAMP, nullable=False)
    value = Column(Numeric(12, 4), nullable=False)
    quality_status = Column(String(30), default="valid")
    created_at = Column(TIMESTAMP, nullable=True)
