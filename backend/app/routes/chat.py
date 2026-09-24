"""Atomic user/assistant exchanges stored in SQLite."""

from datetime import datetime, timezone
import json
import os
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict

from ..database import get_connection
from ..services.context_builder import read_context, format_context, order
from ..services.companion_prompt import build_messages
from ..services.ollama_client import OllamaUnavailable, generate_reply
from ..services.chat_performance import ChatPerformance
from .measurements import NonBlank, Timestamp, require_user

class ChatPerformanceRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def profiled(request):
            if request.method != 'POST':
                return await handler(request)
            performance = ChatPerformance()
            request.state.chat_performance = performance
            try:
                response = await handler(request)
            finally:
                metrics = performance.finish()
            if (response.status_code < 400
                    and os.environ.get('CHAT_PERF_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}):
                result = json.loads(response.body)
                result['performance'] = metrics
                response.body = json.dumps(result, ensure_ascii=False, allow_nan=False,
                                           separators=(',', ':')).encode('utf-8')
                response.headers['content-length'] = str(len(response.body))
            return response

        return profiled


router = APIRouter(prefix="/api/chat", tags=["chat"], route_class=ChatPerformanceRoute)


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


class ChatProfiledReply(ChatReply):
    performance: dict[str, int | float | None] | None = None


def save_message(connection, user_id, role, content):
    message = {"id": "MSG-" + str(uuid4()), "user_id": user_id, "role": role,
               "content": content, "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")}
    connection.execute("INSERT INTO chat_messages (id, user_id, role, content, timestamp) "
                       "VALUES (:id, :user_id, :role, :content, :timestamp)", message)
    return message


@router.post("", response_model=ChatProfiledReply, response_model_exclude_unset=True,
             responses={503: {"description": "Ollama indisponible"}})
def post_chat(body: ChatInput, request: Request):
    performance = request.state.chat_performance
    try:
        with performance.active():
            with performance.measure('context_ms'):
                with get_connection(request.app.state.database_path) as connection:
                    data = read_context(connection, body.user_id)
                context = format_context(data)
            with performance.measure('prompt_ms'):
                messages = build_messages(context, body.message)
            performance.metrics['prompt_chars'] = sum(len(item['content']) for item in messages)
            with performance.measure('ollama_ms'):
                reply = generate_reply(messages)
            with performance.measure('persist_ms'):
                with get_connection(request.app.state.database_path) as connection:
                    # Only persistence holds a write lock; both messages commit together.
                    connection.execute("BEGIN IMMEDIATE")
                    require_user(connection, body.user_id)
                    save_message(connection, body.user_id, "user", body.message)
                    result = save_message(connection, body.user_id, "assistant", reply)
            result = {key: value for key, value in result.items() if key != "id"}
    except OllamaUnavailable as exc:
        # Generation failed before either message was inserted.
        raise HTTPException(503, str(exc)) from exc
    return result


@router.get("/{user_id}", response_model=list[ChatMessage])
def get_chat(user_id: str, request: Request):
    with get_connection(request.app.state.database_path) as connection:
        require_user(connection, user_id)
        return [dict(row) for row in connection.execute(
            "SELECT id, user_id, role, content, timestamp FROM chat_messages WHERE user_id = ? "
            f"ORDER BY {order('timestamp')}", (user_id,))]
