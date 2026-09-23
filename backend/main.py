import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
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
    session_id: str | None = None


class PsychoSpaceCheckin(BaseModel):
    sleep_hours: float
    mood: float
    fatigue: float
    stress: float


PSYCHOSPACE_HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "psychospace_history.json"
PSYCHOSPACE_HISTORY: list[dict] = []
SESSION_MEMORY: dict[str, list[dict]] = {}


def load_psychospace_history() -> list[dict]:
    if not PSYCHOSPACE_HISTORY_FILE.exists():
        PSYCHOSPACE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        PSYCHOSPACE_HISTORY_FILE.write_text("[]", encoding="utf-8")
        return []

    try:
        with PSYCHOSPACE_HISTORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_psychospace_history(history: list[dict]) -> None:
    PSYCHOSPACE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PSYCHOSPACE_HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def evaluate_psychospace_state(sleep_hours: float, mood: float, fatigue: float, stress: float) -> dict:
    sleep_hours = max(0.0, float(sleep_hours))
    mood = max(0.0, float(mood))
    fatigue = max(0.0, float(fatigue))
    stress = max(0.0, float(stress))

    score = 100
    score -= max(0, (7.0 - sleep_hours) * 12)
    score -= max(0, (7.0 - mood) * 10)
    score -= max(0, (fatigue - 5.0) * 10)
    score -= max(0, (stress - 5.0) * 9)
    score = max(0, min(100, int(round(score))))

    if sleep_hours < 5.0 or fatigue >= 8.0 or mood <= 3.0 or stress >= 9.0:
        risk_level = "critical"
        summary = "Signe de vigilance forte : sommeil insuffisant, charge mentale élevée ou humeur très basse."
        action = "Réduire la charge cognitive, sécuriser les tâches critiques et demander un suivi humain immédiat."
    elif sleep_hours < 6.0 or fatigue >= 6.5 or mood <= 5.0 or stress >= 7.0:
        risk_level = "elevated"
        summary = "État de vigilance modérée : la fatigue et le stress augmentent, il faut réajuster la journée."
        action = "Privilégier un repos court, réduire les charges critiques et surveiller la tendance sur 24 à 48 h."
    elif sleep_hours >= 7.0 and mood >= 6.0 and fatigue <= 5.5 and stress <= 6.5:
        risk_level = "stable"
        summary = "État global stable. La charge mentale et le sommeil restent dans une plage exploitable."
        action = "Maintenir la routine, la cohésion et les pauses régulières."
    else:
        risk_level = "watch"
        summary = "État global acceptable mais à surveiller. Une légère dérive reste possible."
        action = "Suivre la tendance, préserver les pauses et rester attentif aux signaux de fatigue."

    return {
        "score": score,
        "risk_level": risk_level,
        "summary": summary,
        "action": action,
        "sleep_hours": round(sleep_hours, 1),
        "mood": round(mood, 1),
        "fatigue": round(fatigue, 1),
        "stress": round(stress, 1),
    }


app = FastAPI(
    title="ARIA",
    description="AI Assistant for a simulated spacecraft",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/assistant/brief")
def get_assistant_brief():
    return {
        "role": "ARIA",
        "mode": "offline_local",
        "mission_focus": [
            "HumanTech & HealthTech",
            "PsychoSpace",
            "Health monitoring",
            "Crew support"
        ],
        "status": "mission-ready",
        "risk_level": "watch",
        "summary": "ARIA est un assistant de bord local conçu pour surveiller la santé psychologique, la fatigue, le sommeil et les procédés de sécurité sans dépendre d'Internet. Il accompagne les astronautes avec un raisonnement prudent, des recommandations concrètes et un mode de secours hors ligne.",
    }


@app.get("/assistant/psychospace/history")
def get_psychospace_history():
    global PSYCHOSPACE_HISTORY
    PSYCHOSPACE_HISTORY = load_psychospace_history()
    return {
        "history": PSYCHOSPACE_HISTORY[-7:],
    }


@app.post("/assistant/psychospace/evaluate")
def evaluate_psychospace(payload: PsychoSpaceCheckin):
    global PSYCHOSPACE_HISTORY
    PSYCHOSPACE_HISTORY = load_psychospace_history()

    result = evaluate_psychospace_state(
        payload.sleep_hours,
        payload.mood,
        payload.fatigue,
        payload.stress,
    )
    entry = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "score": result["score"],
        "risk_level": result["risk_level"],
        "sleep_hours": result["sleep_hours"],
        "mood": result["mood"],
        "fatigue": result["fatigue"],
        "stress": result["stress"],
    }
    PSYCHOSPACE_HISTORY.append(entry)
    if len(PSYCHOSPACE_HISTORY) > 7:
        PSYCHOSPACE_HISTORY[:] = PSYCHOSPACE_HISTORY[-7:]
    save_psychospace_history(PSYCHOSPACE_HISTORY)

    result["history"] = PSYCHOSPACE_HISTORY[-7:]
    return result


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

    session_id = (payload.session_id or "default").strip() or "default"
    session_history = SESSION_MEMORY.setdefault(session_id, [])

    context = knowledge_base.build_context(message, top_k=3)
    recent_context = "\n".join(
        f"{turn['role']}: {turn['content']}" for turn in session_history[-6:]
    )

    system_prompt = """
Tu es ARIA, l'assistant de bord local d'une mission spatiale.
Tu soutiens l'équipage dans le cadre du pilier HumanTech & HealthTech, avec un accent sur le bien-être, la fatigue, le sommeil, le stress, la sécurité et les procédures médicales.
Tu dois répondre en français, de façon naturelle, calme et utile.
Base-toi uniquement sur le contexte mission local fourni et sur la mémoire récente de cette session.
Ne fais pas d'hypothèses. Si tu manques d'information, dis-le clairement.
Réponds en 2 à 5 phrases maximum, ou en 3 points très clairs si la demande demande une action.
Priorise la sécurité, l'action concrète, la clarté et la prévention.
"""

    user_prompt = f"""
Question de l'astronaute : {message}

Mémoire récente de la session :
{recent_context}

Contexte documentaire local :
{context}

Réponds directement, avec un ton conversationnel, professionnel et concise.
Si c'est une demande d'action, donne la priorité, la cause probable et la bonne mesure à prendre.
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:1b",
                "prompt": system_prompt + "\n\n" + user_prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 180},
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

    session_history.append({"role": "user", "content": message})
    session_history.append({"role": "assistant", "content": answer})
    if len(session_history) > 12:
        session_history[:] = session_history[-12:]

    return {
        "message": message,
        "answer": answer,
        "knowledge_context_used": context,
        "session_id": session_id,
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