from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import requests

from backend.ship.ship_state import ship
from backend.knowledge_base import MissionKnowledgeBase
from backend.voice_assistant import VoiceAssistant
from database.db import (
    get_astronaut_context,
    get_astronaut_onboarding_history,
    save_drift_result,
    get_drift_history,
)
from drift import DriftEngine
from backend.analysis.mapping import map_checkin_to_metrics, build_baseline_input
from baseline import BaselineManager


class ChatRequest(BaseModel):
    message: str


app = FastAPI(
    title="ARIA",
    description="AI Assistant for a simulated spacecraft",
    version="0.1.0"
)

knowledge_base = MissionKnowledgeBase()
voice_assistant = VoiceAssistant()


@app.get("/")
def root():
    return {"name": "ARIA", "status": "online"}


@app.get("/assistant/knowledge")
def get_knowledge_summary():
    return {
        "total_entries": len(knowledge_base.entries),
        "categories": sorted({entry.get("category", "general") for entry in knowledge_base.entries}),
    }


@app.post("/assistant/search")
def search_knowledge(payload: dict):
    query = str(payload.get("query", "")).strip()
    if not query:
        raise HTTPException(status_code=400, detail="Une requête est requise.")
    return {"query": query, "matches": knowledge_base.search(query, top_k=5)}


@app.post("/assistant/chat")
def chat_with_aria(payload: ChatRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Le message ne peut pas être vide.")

    context = knowledge_base.build_context(message, top_k=5)

    system_prompt = """
Tu es ARIA, un assistant autonome de bord pour une mission spatiale.
Tu travailles entièrement en local et tu ne dois pas dépendre d'Internet.
Tu dois toujours te baser sur la documentation locale et sur le contexte mission fourni.
Tu ne dois pas inventer d'informations.
Réponds en français.
Garde une réponse claire, calme, opérationnelle et précise.
Si tu ne sais pas, dis-le honnêtement.
"""

    user_prompt = f"""
Question de l'astronaute : {message}

Contexte documentaire local :
{context}

Réponds de manière utile, structurée et concise.
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:1b",
                "prompt": system_prompt + "\n\n" + user_prompt,
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("response", "Je n'ai pas pu générer de réponse locale.")
    except Exception:
        answer = (
            "ARIA est disponible localement mais le modèle Ollama n'est pas accessible "
            "à l'instant. Vérifie que 'ollama serve' tourne bien sur le PC."
        )

    return {
        "message": message,
        "answer": answer,
        "knowledge_context_used": context,
    }


@app.get("/assistant/voice/status")
def get_voice_status():
    return {
        "available": voice_assistant.is_available(),
        "tts_available": voice_assistant.engine is not None,
        "stt_available": voice_assistant.recognizer is not None,
    }


@app.post("/assistant/voice/say")
def speak_text(payload: dict):
    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="Le texte à lire est vide.")
    return {"spoken": voice_assistant.speak(text)}


@app.post("/assistant/voice/transcribe")
def transcribe_audio(audio: UploadFile = File(default=None)):
    if audio is None:
        raise HTTPException(status_code=400, detail="Aucun fichier audio fourni.")

    if voice_assistant.recognizer is None:
        return {"text": "", "error": "speech_recognition n'est pas installé dans cet environnement."}

    try:
        contents = audio.file.read()
        path = f"/tmp/{audio.filename or 'aria_voice.wav'}"
        with open(path, "wb") as handle:
            handle.write(contents)

        import wave
        from pathlib import Path

        if not Path(path).exists():
            return {"text": "", "error": "Le fichier audio n'a pas pu être créé."}

        import speech_recognition as sr
        with sr.AudioFile(path) as source:
            audio_data = voice_assistant.recognizer.record(source)
        text = voice_assistant.recognizer.recognize_google(audio_data, language="fr-FR")
        return {"text": text}
    except Exception as exc:  # pragma: no cover
        return {"text": "", "error": str(exc)}


@app.get("/ship/status")
def get_ship_status():
    return ship.get_status()


@app.get("/ship/energy")
def get_energy():
    return ship.energy.get_status()


@app.get("/ship/oxygen")
def get_oxygen():
    return ship.oxygen.get_status()


@app.get("/ship/water")
def get_water():
    return ship.water.get_status()


@app.get("/ship/temperature")
def get_temperature():
    return ship.temperature.get_status()


@app.get("/astronaut/{astronaut_id}/context")
def get_astronaut_context_api(astronaut_id: int):

    context = get_astronaut_context(astronaut_id)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Astronaute {astronaut_id} introuvable"
        )

    return dict(context)


@app.get("/astronaut/{astronaut_id}/drift")
def get_astronaut_drift(astronaut_id: int):

    today_checkin = get_astronaut_context(astronaut_id)

    if today_checkin is None:
        raise HTTPException(
            status_code=404,
            detail=f"Astronaute {astronaut_id} introuvable"
        )

    onboarding_days = 7

    history = get_astronaut_onboarding_history(
        astronaut_id,
        onboarding_days=onboarding_days,
    )

    if len(history) < onboarding_days:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Pas assez de données pour calculer une baseline "
                f"({len(history)}/{onboarding_days} jours)."
            )
        )

    baseline_input = build_baseline_input(history)
    today_metrics = map_checkin_to_metrics(today_checkin)

    baseline_mgr = BaselineManager(onboarding_days=onboarding_days)
    baseline = baseline_mgr.calculate_initial_baseline(baseline_input)

    drift_engine = DriftEngine(weights={
        "sommeil_h": 0.3125,
        "humeur": 0.25,
        "fatigue": 0.25,
        "activite": 0.1875,
    })

    z_today = drift_engine.evaluate_daily_signals(today_metrics, baseline)

    save_drift_result(
        astronaut_id,
        today_checkin["checkin_date"],
        z_today["z_scores"],
        z_today["concerning_signals"],
    )

    history_z_scores = get_drift_history(astronaut_id, days=14)

    drift_result = drift_engine.evaluate_drift_with_context(history_z_scores)

    return {
        "astronaut_id": astronaut_id,
        "checkin_date": str(today_checkin["checkin_date"]),
        "baseline": baseline,
        "today_metrics": today_metrics,
        "drift_result": drift_result,
    }