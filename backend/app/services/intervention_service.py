"""Read-only, explainable recommendations. No LLM, scores or automatic writes."""

import json
import re
import unicodedata

from ..database import get_connection
from ..routes.measurements import require_user
from .context_builder import order


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


def memory_rule(memory, signals):
    """Conservative FR/EN patterns; unrecognized or negative statements are not preferences."""
    if memory["source"] not in {"user", "user_chat", "user_correction"}:
        return None
    text = normalized(memory["content"])
    if re.search(r"\b(ne|pas|jamais|sans|non|not|never|no|avoid|eviter)\b|n['’]|n['’]t", text):
        return None
    support = memory["category"] in {"support_preference", "coping_strategy"}
    helps = re.search(r"\b(aide|aident|helps|help|helpful)\b", text)
    if support and helps and re.search(r"\b(musique|music)\b", text) and signals & {"stress", "fatigue"}:
        return "music_break", "Si tu le souhaites, tu peux prendre quelques minutes pour écouter une musique que tu apprécies.", sorted(signals & {"stress", "fatigue"})
    if support and helps and re.search(r"activite physique|physical activity|exercise|sport", text) and signals & {"activity_minutes", "activity", "energy"}:
        return "short_activity", "Si tu en as envie, tu peux essayer quelques minutes de mouvement doux, à ton rythme.", sorted(signals & {"activity_minutes", "activity", "energy"})
    if memory["category"] in {"support_preference", "coping_strategy", "communication_preference"}:
        if re.search(r"\b(prefere|besoin|prefer|prefers|need|needs)\b", text) and re.search(r"temps seul|besoin d.espace|time alone|space", text):
            return "quiet_break", "Si tu en ressens le besoin, tu peux prendre quelques minutes au calme avant de discuter.", []
    return None


def recommend_intervention(database_path, user_id):
    """Return an internal proposal, or None without a drift; caller explicitly creates it."""
    with get_connection(database_path) as connection:
        require_user(connection, user_id)
        row = connection.execute(
            "SELECT id, level, affected_signals FROM drift_events WHERE user_id = ? "
            f"ORDER BY {order('detected_at', True, 'id')} LIMIT 1", (user_id,),
        ).fetchone()
        if row is None:
            return None
        drift = dict(row)
        memories = [dict(item) for item in connection.execute(
            "SELECT id, category, content, importance, source FROM memories WHERE user_id = ? "
            "ORDER BY importance DESC, id ASC", (user_id,))]
    signals = set(json.loads(drift["affected_signals"] or "[]"))
    for memory in memories:
        rule = memory_rule(memory, signals)
        if rule:
            kind, message, matched = rule
            return {
                "user_id": user_id, "drift_event_id": drift["id"], "type": kind, "message": message,
                "memory_id": memory["id"],
                "explanation": {
                    "affected_signals": matched, "memory_content": memory["content"],
                    "selection": "Mémoire explicite pertinente, importance décroissante puis id croissant. "
                                 "Les conditions de la mémoire ne sont pas présumées présentes.",
                },
            }
    return {
        "user_id": user_id, "drift_event_id": drift["id"], "type": "quiet_break",
        "message": "Si tu le souhaites, tu peux prendre quelques minutes au calme. Tu restes libre de refuser.",
        "memory_id": None,
        "explanation": {"affected_signals": sorted(signals), "memory_content": None,
                        "selection": "Aucune préférence reconnue et pertinente : proposition générique, sans préférence supposée."},
    }
