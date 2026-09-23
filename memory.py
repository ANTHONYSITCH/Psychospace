class AstronautMemory:

    def __init__(self):
        # En production, ces données pourront venir de SQLite.
        self.memories = {
            "ASTRO-01": {
                "name": "Sarah",
                "preferences": [
                    "Musique classique",
                    "Café noir le matin",
                    "Temps seul avant discussion"
                ],
                "life_events": [
                    "Anniversaire fille : 14 Octobre"
                ],
                "effective_coping_strategies": [
                    "Exercice physique modéré",
                    "Isolement court (30 min)"
                ]
            }
        }

    def get_context_string(self, astronaut_id):

        astro = self.memories.get(astronaut_id, {})

        if not astro:
            return "Aucune mémoire spécifique enregistrée."

        return (
            f"Astronaute : {astro.get('name')}\n"
            f"- Préférences : "
            f"{', '.join(astro.get('preferences', []))}\n"
            f"- Événements : "
            f"{', '.join(astro.get('life_events', []))}\n"
            f"- Stratégies efficaces passées : "
            f"{', '.join(astro.get('effective_coping_strategies', []))}"
        )