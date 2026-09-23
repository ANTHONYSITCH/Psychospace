"""Shared validation for the two timestamped measurement contracts."""

import re
from datetime import datetime
from typing import Annotated

from fastapi import HTTPException
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("La valeur ne doit pas être vide.")
    return value


def utc_timestamp(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
        raise ValueError("Date ISO 8601 UTC attendue, avec suffixe Z.")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


NonBlank = Annotated[str, AfterValidator(non_blank)]
Timestamp = Annotated[str, AfterValidator(utc_timestamp)]
Score = Annotated[int, Field(ge=1, le=10)]
NonNegative = Annotated[float, Field(ge=0)]


class Measurement(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    user_id: NonBlank
    timestamp: Timestamp


def require_user(connection, user_id: str) -> None:
    if not user_id.strip():
        raise HTTPException(400, "Identifiant utilisateur vide.")
    if connection.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone() is None:
        raise HTTPException(404, "Utilisateur introuvable.")


# UTC dates: sort whole seconds, then the optional fraction, then insertion id.
# CAST('Z' AS REAL) is zero; CAST('.123Z' AS REAL) is 0.123.
TIME_ORDER = "substr(timestamp, 1, 19), CAST(substr(timestamp, 20) AS REAL), id"
