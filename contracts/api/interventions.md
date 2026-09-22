# Contrat API — interventions

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## GET /api/interventions/{user_id}

Retourner les propositions de soutien.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Tableau d'objets [intervention](../data/intervention.example.json), trié par created_at croissant.

### Exemple de requête

```http
GET /api/interventions/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
[
  {
    "id": "INT-001",
    "user_id": "ASTRO-001",
    "drift_event_id": "DRIFT-001",
    "created_at": "2026-09-22T19:00:00Z",
    "type": "music_break",
    "message": "Alex, souhaites-tu prendre dix minutes pour écouter une musique que tu apprécies ?",
    "accepted": false,
    "completed": false
  }
]
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## POST /api/interventions

Créer une proposition de soutien.

**Données attendues et résultat :** Corps complet intervention. id est fourni par le composant appelant et doit être unique. drift_event_id doit référencer un événement du même user_id. accepted et completed sont des booléens JSON ; completed=true exige accepted=true. message est une chaîne non vide.

### Exemple de requête

```http
POST /api/interventions HTTP/1.1
Content-Type: application/json

{
  "id": "INT-001",
  "user_id": "ASTRO-001",
  "drift_event_id": "DRIFT-001",
  "created_at": "2026-09-22T19:00:00Z",
  "type": "music_break",
  "message": "Alex, souhaites-tu prendre dix minutes pour écouter une musique que tu apprécies ?",
  "accepted": false,
  "completed": false
}
```

### Exemple de réponse — 201

```json
{
  "id": "INT-001",
  "user_id": "ASTRO-001",
  "drift_event_id": "DRIFT-001",
  "created_at": "2026-09-22T19:00:00Z",
  "type": "music_break",
  "message": "Alex, souhaites-tu prendre dix minutes pour écouter une musique que tu apprécies ?",
  "accepted": false,
  "completed": false
}
```

**Codes HTTP :** 201 : création réussie. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également pour un identifiant déjà utilisé, un événement d'un autre utilisateur ou des booléens incohérents.

## PATCH /api/interventions/{intervention_id}

Mettre à jour l'acceptation ou la réalisation d'une proposition.

**Données attendues et résultat :** intervention_id dans le chemin correspond à id. Corps partiel contenant au moins accepted ou completed, exclusivement des booléens JSON. Aucun autre champ autorisé ; les champs omis restent inchangés. L'état final doit respecter completed=true uniquement si accepted=true. Réponse : objet intervention complet après mise à jour.

### Exemple de requête

```http
PATCH /api/interventions/INT-001 HTTP/1.1
Content-Type: application/json

{
  "accepted": true,
  "completed": false
}
```

### Exemple de réponse — 200

```json
{
  "id": "INT-001",
  "user_id": "ASTRO-001",
  "drift_event_id": "DRIFT-001",
  "created_at": "2026-09-22T19:00:00Z",
  "type": "music_break",
  "message": "Alex, souhaites-tu prendre dix minutes pour écouter une musique que tu apprécies ?",
  "accepted": true,
  "completed": false
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également pour un corps vide, un champ non autorisé ou un état final incohérent.
