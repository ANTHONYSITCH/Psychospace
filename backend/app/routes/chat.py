"""Atomic user/assistant exchanges stored in SQLite."""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from ..database import get_connection
from ..services.context_builder import read_context, format_context, order
from ..services.companion_prompt import build_messages
from ..services.ollama_client import OllamaUnavailable, generate_reply
from .measurements import NonBlank, Timestamp, require_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    user_id: NonBlank
    message: NonBlank


class ChatReply(BaseModel):
    user_id: str
    role: Literal["assistant"]
    content: str
    timestamp: Timestamp


class ChatMessage(ChatReply):
    id: str
    role: Literal["user", "assistant"]


def save_message(connection, user_id, role, content):
    message = {"id": "MSG-" + str(uuid4()), "user_id": user_id, "role": role,
               "content": content, "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")}
    connection.execute("INSERT INTO chat_messages (id, user_id, role, content, timestamp) "
                       "VALUES (:id, :user_id, :role, :content, :timestamp)", message)
    return message


@router.post("", response_model=ChatReply, responses={503: {"description": "Ollama indisponible"}})
def post_chat(body: ChatInput, request: Request):
    try:
        with get_connection(request.app.state.database_path) as connection:
            data = read_context(connection, body.user_id)
        context = format_context(data)
        reply = generate_reply(build_messages(context, body.message))
        with get_connection(request.app.state.database_path) as connection:
            # Only persistence holds a write lock; both messages commit together.
            connection.execute("BEGIN IMMEDIATE")
            require_user(connection, body.user_id)
            save_message(connection, body.user_id, "user", body.message)
            result = save_message(connection, body.user_id, "assistant", reply)
        return {key: value for key, value in result.items() if key != "id"}
    except OllamaUnavailable as exc:
        # Generation failed before either message was inserted.
        raise HTTPException(503, str(exc)) from exc


@router.get("/{user_id}", response_model=list[ChatMessage])
def get_chat(user_id: str, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, user_id)
        return [dict(row) for row in connection.execute(
            "SELECT id, user_id, role, content, timestamp FROM chat_messages WHERE user_id = ? "
            f"ORDER BY {order('timestamp')}", (user_id,))]
