"""Explicit, user-controlled support proposals following the shared contract."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, model_validator

from ..database import get_connection
from ..services.context_builder import order
from .measurements import NonBlank, Timestamp, require_user

router = APIRouter(prefix="/api/interventions", tags=["interventions"])
COLUMNS = "id, user_id, drift_event_id, created_at, type, message, accepted, completed"


def validate_state(accepted, completed):
    if completed and not accepted:
        raise HTTPException(400, "Une intervention terminée doit être acceptée.")


class Intervention(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: NonBlank
    user_id: NonBlank
    drift_event_id: NonBlank
    created_at: Timestamp
    type: NonBlank
    message: NonBlank
    accepted: bool
    completed: bool


class InterventionPatch(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    # Defaults permit omission; explicit null still fails strict bool validation.
    accepted: bool = False
    completed: bool = False

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("Au moins un état est requis.")
        return self


def serialize(row):
    result = dict(row)
    result["accepted"] = bool(result["accepted"])
    result["completed"] = bool(result["completed"])
    return result


@router.get("/{user_id}", response_model=list[Intervention])
def get_interventions(user_id: str, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, user_id)
        return [serialize(row) for row in connection.execute(
            f"SELECT {COLUMNS} FROM interventions WHERE user_id = ? "
            f"ORDER BY {order('created_at', tie_breaker='id')}", (user_id,))]


@router.post("", response_model=Intervention, status_code=201)
def create_intervention(body: Intervention, request: Request):
    validate_state(body.accepted, body.completed)
    with get_connection(request.app.state.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        require_user(connection, body.user_id)
        drift = connection.execute("SELECT user_id FROM drift_events WHERE id = ?", (body.drift_event_id,)).fetchone()
        if drift is None:
            raise HTTPException(404, "Événement de dérive introuvable.")
        if drift["user_id"] != body.user_id:
            raise HTTPException(400, "Cet événement appartient à un autre utilisateur.")
        if connection.execute("SELECT 1 FROM interventions WHERE id = ?", (body.id,)).fetchone():
            raise HTTPException(400, "Cet identifiant d'intervention est déjà utilisé.")
        connection.execute(
            f"INSERT INTO interventions ({COLUMNS}) VALUES "
            "(:id, :user_id, :drift_event_id, :created_at, :type, :message, :accepted, :completed)",
            body.model_dump(),
        )
    return body


@router.patch("/{intervention_id}", response_model=Intervention)
def patch_intervention(intervention_id: str, body: InterventionPatch, request: Request):
    if not intervention_id.strip():
        raise HTTPException(400, "Identifiant d'intervention vide.")
    with get_connection(request.app.state.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(f"SELECT {COLUMNS} FROM interventions WHERE id = ?", (intervention_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Intervention introuvable.")
        result = {**serialize(row), **body.model_dump(exclude_unset=True)}
        validate_state(result["accepted"], result["completed"])
        connection.execute("UPDATE interventions SET accepted = ?, completed = ? WHERE id = ?",
                           (result["accepted"], result["completed"], intervention_id))
    return result
