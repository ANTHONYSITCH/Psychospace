from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


class MissionKnowledgeBase:
    """Simple local RAG-style knowledge base for ARIA."""

    SYNONYMS = {
        "oxygene": {"oxygene", "oxygen", "air", "respiration", "dioxygene"},
        "energie": {"energie", "energy", "puissance", "batterie", "electrique", "electricite"},
        "eau": {"eau", "water", "hydration", "reservoir"},
        "temperature": {"temperature", "thermique", "chaleur", "froid", "ventilation"},
        "fatigue": {"fatigue", "sommeil", "repos", "vigilance", "charge", "sleep"},
        "humeur": {"humeur", "moral", "mood", "bienetre", "bien-être", "stress", "affect"},
        "communication": {"communication", "comms", "signal", "liaison", "radio", "contact"},
        "mission": {"mission", "objectif", "trajet", "rotation", "opération", "operation"},
    }

    def __init__(self, base_dir: str | None = None):
        root_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.knowledge_path = root_dir / "knowledge" / "mission_knowledge.json"
        self.entries: List[Dict[str, Any]] = []
        self._load()

    def _normalize_text(self, value: str) -> str:
        if not value:
            return ""
        lowered = value.lower()
        lowered = lowered.replace("é", "e").replace("è", "e").replace("ê", "e")
        lowered = lowered.replace("à", "a").replace("â", "a").replace("ç", "c")
        lowered = lowered.replace("ù", "u").replace("î", "i").replace("ï", "i")
        lowered = lowered.replace("ô", "o").replace("ö", "o")
        lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _query_terms(self, query: str) -> set[str]:
        tokens = set(self._normalize_text(query).split())
        expanded: set[str] = set(tokens)
        for token in list(tokens):
            for canonical, variants in self.SYNONYMS.items():
                if token in variants or token == canonical:
                    expanded.add(canonical)
                    expanded.update(variants)
        return expanded

    def _entry_text(self, entry: Dict[str, Any]) -> str:
        parts = [str(entry.get("title", "")), str(entry.get("category", "")), str(entry.get("content", ""))]
        return self._normalize_text(" ".join(parts))

    def _score_entry(self, query_terms: set[str], entry: Dict[str, Any]) -> float:
        text = self._entry_text(entry)
        score = 0.0

        if not query_terms:
            return score

        for term in query_terms:
            if not term:
                continue
            if term in text:
                score += 2.0
            if " " in term:
                if term in text:
                    score += 3.0

        for canonical, variants in self.SYNONYMS.items():
            if canonical in query_terms:
                if canonical in text:
                    score += 4.0
                for variant in variants:
                    if variant in text and variant in query_terms:
                        score += 2.0

        title = self._normalize_text(str(entry.get("title", "")))
        category = self._normalize_text(str(entry.get("category", "")))
        for term in query_terms:
            if term in title:
                score += 5.0
            if term in category:
                score += 3.0

        return score

    def _load(self) -> None:
        if not self.knowledge_path.exists():
            self.entries = [
                {
                    "title": "Mission default",
                    "category": "general",
                    "content": "ARIA est un assistant autonome pour l'équipage en mission spatiale. Elle doit aider à la sécurité, au bien-être, au suivi des systèmes et aux procédures d'urgence.",
                }
            ]
            return

        with self.knowledge_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            self.entries = data.get("entries", []) if isinstance(data, dict) else data

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query:
            return []

        query_terms = self._query_terms(query)
        scored: List[tuple[float, Dict[str, Any]]] = []

        for entry in self.entries:
            score = self._score_entry(query_terms, entry)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def build_context(self, query: str, top_k: int = 3) -> str:
        matches = self.search(query, top_k=top_k)
        if not matches:
            return "Aucune donnée documentaire locale n'a été trouvée pour cette requête."

        blocks = []
        for idx, match in enumerate(matches, start=1):
            title = match.get("title", "Document")
            category = match.get("category", "général")
            content = match.get("content", "")
            blocks.append(f"[{idx}] {category} - {title}\n{content}")

        return "\n\n".join(blocks)


if __name__ == "__main__":
    kb = MissionKnowledgeBase()
    print(kb.build_context("oxygen et energie", top_k=3))
