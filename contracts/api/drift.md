# Contrat API — drift

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## GET /api/drift/{user_id}

Retourner les événements de changement comportemental.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Tableau d'objets [drift-event](../data/drift-event.example.json), trié par detected_at croissant.

### Exemple de requête

```http
GET /api/drift/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
[
  {
    "id": "DRIFT-001",
    "user_id": "ASTRO-001",
    "detected_at": "2026-09-22T18:01:00Z",
    "level": "moderate",
    "drift_score": 0.65,
    "confidence": 0.75,
    "affected_signals": [
      "sleep_hours",
      "stress",
      "fatigue",
      "energy"
    ],
    "explanation": "Le bilan du jour indique un sommeil plus court, un stress et une fatigue plus élevés, ainsi qu'une énergie plus faible que les moyennes personnelles des 14 jours précédents.",
    "status": "open"
  }
]
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## POST /api/drift/{user_id}/analyze

Demander au Drift Engine une analyse des données récentes.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Analyse synchrone par rapport aux habitudes personnelles. Si un changement est détecté, réponse complète drift-event. level : low, moderate ou high ; drift_score et confidence : nombres entre 0 et 1 ; affected_signals : tableau de chaînes ; status : open, acknowledged ou resolved. Les valeurs sont produites par le moteur ; aucun seuil ni algorithme n'est défini ici. Aucun diagnostic médical ou psychiatrique, notamment dans explanation.

### Exemple de requête

```http
POST /api/drift/ASTRO-001/analyze HTTP/1.1
```

### Exemple de réponse — 200

```json
{
  "id": "DRIFT-001",
  "user_id": "ASTRO-001",
  "detected_at": "2026-09-22T18:01:00Z",
  "level": "moderate",
  "drift_score": 0.65,
  "confidence": 0.75,
  "affected_signals": [
    "sleep_hours",
    "stress",
    "fatigue",
    "energy"
  ],
  "explanation": "Le bilan du jour indique un sommeil plus court, un stress et une fatigue plus élevés, ainsi qu'une énergie plus faible que les moyennes personnelles des 14 jours précédents.",
  "status": "open"
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également si les observations ou la référence sont insuffisantes. 204 : analyse terminée sans changement détecté, aucun corps et aucun événement artificiel.
