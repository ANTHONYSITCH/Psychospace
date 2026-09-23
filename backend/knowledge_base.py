from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Dict


class MissionKnowledgeBase:
    """Simple local RAG-style knowledge base for ARIA."""

    def __init__(self, base_dir: str | None = None):
        root_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.knowledge_path = root_dir / "knowledge" / "mission_knowledge.json"
        self.entries: List[Dict[str, Any]] = []
        self._load()

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

        lowered_query = query.lower()
        scored: List[tuple[float, Dict[str, Any]]] = []

        for entry in self.entries:
            text = " ".join(
                str(value).lower()
                for value in entry.values()
                if isinstance(value, (str, int, float))
            )
            score = 0.0

            for token in lowered_query.split():
                if token in text:
                    score += 1.0

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def build_context(self, query: str, top_k: int = 5) -> str:
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
    print(kb.build_context("oxygène et énergie", top_k=3))
