"""User-managed memories; no automatic collection or extraction."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from ..database import get_connection
from .measurements import NonBlank, Score, Timestamp, require_user

router = APIRouter(prefix="/api/memories", tags=["memories"])
COLUMNS = "id, user_id, category, content, importance, source, created_at"


class Memory(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: NonBlank
    user_id: NonBlank
    category: NonBlank
    content: NonBlank
    importance: Score
    source: NonBlank
    created_at: Timestamp


@router.get("/{user_id}", response_model=list[Memory])
def get_memories(user_id: str, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, user_id)
        rows = connection.execute(
            f"SELECT {COLUMNS} FROM memories WHERE user_id = ? "
            "ORDER BY substr(created_at, 1, 19), CAST(substr(created_at, 20) AS REAL), id",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=Memory, status_code=201)
def create_memory(memory: Memory, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        require_user(connection, memory.user_id)
        if connection.execute("SELECT 1 FROM memories WHERE id = ?", (memory.id,)).fetchone():
            raise HTTPException(400, "Cet identifiant de mémoire est déjà utilisé.")
        connection.execute(
            f"INSERT INTO memories ({COLUMNS}) "
            "VALUES (:id, :user_id, :category, :content, :importance, :source, :created_at)",
            memory.model_dump(),
        )
    return memory


@router.put("/{memory_id}", response_model=Memory)
def update_memory(memory_id: str, memory: Memory, request: Request):
    if not memory_id.strip():
        raise HTTPException(400, "Identifiant de mémoire vide.")
    with get_connection(request.app.state.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            f"SELECT {COLUMNS} FROM memories WHERE id = ?", (memory_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(404, "Mémoire introuvable.")
        if any(getattr(memory, field) != existing[field] for field in ("id", "user_id", "created_at")):
            raise HTTPException(400, "id, user_id et created_at ne peuvent pas être modifiés.")
        connection.execute(
            "UPDATE memories SET category = ?, content = ?, importance = ?, source = ? WHERE id = ?",
            (memory.category, memory.content, memory.importance, memory.source, memory_id),
        )
    return memory


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, request: Request):
    if not memory_id.strip():
        raise HTTPException(400, "Identifiant de mémoire vide.")
    with get_connection(request.app.state.database_path) as connection:
        cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Mémoire introuvable.")
    return {"success": True}
