import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from ..database import get_connection

router = APIRouter(prefix="/api/profile", tags=["profile"])


class Profile(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    user_id: str
    first_name: str
    age: int
    mission_id: str
    normal_sleep_hours: float
    preferred_support: str
    preferred_contact_time: str
    interests: list[str]


@router.get("/{user_id}", response_model=Profile)
def get_profile(user_id: str, request: Request):
    if not user_id.strip():
        raise HTTPException(400, "Identifiant utilisateur vide.")
    with get_connection(request.app.state.database_path) as connection:
        row = connection.execute(
            "SELECT u.user_id, u.first_name, u.age, u.mission_id, "
            "p.normal_sleep_hours, p.preferred_support, p.preferred_contact_time, p.interests "
            "FROM users AS u JOIN profiles AS p ON p.user_id = u.user_id "
            "WHERE u.user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Utilisateur ou profil introuvable.")
    result = dict(row)
    result["interests"] = json.loads(result["interests"])
    return result
