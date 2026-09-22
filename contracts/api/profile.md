# Contrat API — profile

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## GET /api/profile/{user_id}

Retourner le profil complet.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Objet profile réunissant les champs de users et profiles, sans users.created_at.

### Exemple de requête

```http
GET /api/profile/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
{
  "user_id": "ASTRO-001",
  "first_name": "Alex",
  "age": 34,
  "mission_id": "MISSION-001",
  "normal_sleep_hours": 7.5,
  "preferred_support": "music",
  "preferred_contact_time": "19:00:00Z",
  "interests": [
    "music",
    "reading",
    "astronomy"
  ]
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## PUT /api/profile/{user_id}

Mettre à jour le profil existant.

**Données attendues et résultat :** Corps complet [profile](../data/profile.example.json). user_id doit correspondre au chemin et reste immuable. interests est un tableau de chaînes ; âge en années, sommeil en heures, heure de contact quotidienne UTC. Aucune création d'utilisateur par cette route.

### Exemple de requête

```http
PUT /api/profile/ASTRO-001 HTTP/1.1
Content-Type: application/json

{
  "user_id": "ASTRO-001",
  "first_name": "Alex",
  "age": 34,
  "mission_id": "MISSION-001",
  "normal_sleep_hours": 7.5,
  "preferred_support": "music",
  "preferred_contact_time": "19:00:00Z",
  "interests": [
    "music",
    "reading",
    "astronomy"
  ]
}
```

### Exemple de réponse — 200

```json
{
  "user_id": "ASTRO-001",
  "first_name": "Alex",
  "age": 34,
  "mission_id": "MISSION-001",
  "normal_sleep_hours": 7.5,
  "preferred_support": "music",
  "preferred_contact_time": "19:00:00Z",
  "interests": [
    "music",
    "reading",
    "astronomy"
  ]
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également si user_id diffère du chemin.
