from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ..services.whisper_service import VoiceError, audio_suffix, max_audio_bytes, transcribe

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(request: Request):
    try:
        content_type = request.headers.get("content-type", "")
        audio_suffix(content_type)
        limit = max_audio_bytes()
        audio = bytearray()
        async for chunk in request.stream():
            if len(audio) + len(chunk) > limit:
                raise VoiceError(413, "L'audio est trop volumineux.")
            audio.extend(chunk)
        return await run_in_threadpool(transcribe, bytes(audio), content_type)
    except VoiceError as error:
        raise HTTPException(error.status, error.message) from None
