# Contrat API — checkins

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## POST /api/checkins

Enregistrer un élément dans les bilans quotidiens.

**Données attendues et résultat :** Corps complet conforme à [daily-checkin.example.json](../data/daily-checkin.example.json). Les cinq indicateurs sont des entiers de 1 à 10 inclus ; sommeil en heures et activité en minutes, positifs ou nuls.

### Exemple de requête

```http
POST /api/checkins HTTP/1.1
Content-Type: application/json

{
  "user_id": "ASTRO-001",
  "timestamp": "2026-09-22T18:00:00Z",
  "sleep_hours": 6,
  "mood": 5,
  "stress": 7,
  "fatigue": 7,
  "energy": 4,
  "social_level": 4,
  "activity_minutes": 25
}
```

### Exemple de réponse — 201

```json
{
  "success": true,
  "checkin_id": 1
}
```

**Codes HTTP :** 201 : création réussie. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## GET /api/checkins/{user_id}

Retourner l'historique des bilans quotidiens.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Tableau d'objets [daily-checkin](../data/daily-checkin.example.json), trié par timestamp croissant. Aucun identifiant SQL ajouté aux objets.

### Exemple de requête

```http
GET /api/checkins/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
[
  {
    "user_id": "ASTRO-001",
    "timestamp": "2026-09-22T18:00:00Z",
    "sleep_hours": 6,
    "mood": 5,
    "stress": 7,
    "fatigue": 7,
    "energy": 4,
    "social_level": 4,
    "activity_minutes": 25
  }
]
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.
