# Contrat API — sensors

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## POST /api/sensors

Enregistrer un élément dans les mesures de capteurs.

**Données attendues et résultat :** Corps complet conforme à [sensor-reading.example.json](../data/sensor-reading.example.json). value est un nombre scalaire ; sensor_type reste extensible : heart_rate / bpm, spo2 / %, movement / m/s². Le type et son unité doivent être convenus en équipe.

### Exemple de requête

```http
POST /api/sensors HTTP/1.1
Content-Type: application/json

{
  "user_id": "ASTRO-001",
  "sensor_type": "heart_rate",
  "value": 82,
  "unit": "bpm",
  "timestamp": "2026-09-22T17:55:00Z"
}
```

### Exemple de réponse — 201

```json
{
  "success": true,
  "sensor_reading_id": 1
}
```

**Codes HTTP :** 201 : création réussie. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## GET /api/sensors/{user_id}

Retourner l'historique des mesures de capteurs.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Tableau d'objets [sensor-reading](../data/sensor-reading.example.json), trié par timestamp croissant. Aucun identifiant SQL ajouté aux objets.

### Exemple de requête

```http
GET /api/sensors/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
[
  {
    "user_id": "ASTRO-001",
    "sensor_type": "heart_rate",
    "value": 82,
    "unit": "bpm",
    "timestamp": "2026-09-22T17:55:00Z"
  }
]
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.
