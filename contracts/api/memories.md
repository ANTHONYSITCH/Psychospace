# Contrat API — memories

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## GET /api/memories/{user_id}

Retourner les mémoires autorisées de l'utilisateur.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Tableau d'objets [memory](../data/memory.example.json), trié par created_at croissant. Les contrats actuels ne décrivent pas de champ de consentement : les critères d'autorisation restent à valider en équipe avant implémentation. Aucun mécanisme d'authentification n'est ajouté.

### Exemple de requête

```http
GET /api/memories/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
[
  {
    "id": "MEM-001",
    "user_id": "ASTRO-001",
    "category": "support_preference",
    "content": "La musique aide Alex lorsqu'il est stressé.",
    "importance": 8,
    "source": "user_chat",
    "created_at": "2026-09-21T19:00:00Z"
  }
]
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## POST /api/memories

Créer une mémoire de personnalisation.

**Données attendues et résultat :** Corps complet memory. id est fourni par le composant appelant et doit être unique ; importance est un entier de 1 à 10 ; content est une chaîne non vide. Réponse : objet créé.

### Exemple de requête

```http
POST /api/memories HTTP/1.1
Content-Type: application/json

{
  "id": "MEM-001",
  "user_id": "ASTRO-001",
  "category": "support_preference",
  "content": "La musique aide Alex lorsqu'il est stressé.",
  "importance": 8,
  "source": "user_chat",
  "created_at": "2026-09-21T19:00:00Z"
}
```

### Exemple de réponse — 201

```json
{
  "id": "MEM-001",
  "user_id": "ASTRO-001",
  "category": "support_preference",
  "content": "La musique aide Alex lorsqu'il est stressé.",
  "importance": 8,
  "source": "user_chat",
  "created_at": "2026-09-21T19:00:00Z"
}
```

**Codes HTTP :** 201 : création réussie. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également si l'identifiant est déjà utilisé.

## PUT /api/memories/{memory_id}

Corriger une mémoire existante.

**Données attendues et résultat :** memory_id dans le chemin correspond à id. Corps complet memory ; id, user_id et created_at restent inchangés. category, content, importance et source peuvent être corrigés. Aucun transfert de mémoire à un autre utilisateur.

### Exemple de requête

```http
PUT /api/memories/MEM-001 HTTP/1.1
Content-Type: application/json

{
  "id": "MEM-001",
  "user_id": "ASTRO-001",
  "category": "support_preference",
  "content": "La musique calme aide Alex lorsqu'il est stressé.",
  "importance": 8,
  "source": "user_chat",
  "created_at": "2026-09-21T19:00:00Z"
}
```

### Exemple de réponse — 200

```json
{
  "id": "MEM-001",
  "user_id": "ASTRO-001",
  "category": "support_preference",
  "content": "La musique calme aide Alex lorsqu'il est stressé.",
  "importance": 8,
  "source": "user_chat",
  "created_at": "2026-09-21T19:00:00Z"
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également si id diffère du chemin ou si un champ immuable est modifié.

## DELETE /api/memories/{memory_id}

Supprimer une mémoire à la demande de l'utilisateur.

**Données attendues et résultat :** memory_id dans le chemin correspond à id ; aucun corps. Le succès confirme la suppression : cette mémoire ne doit plus être retournée ni utilisée pour personnaliser les échanges futurs.

### Exemple de requête

```http
DELETE /api/memories/MEM-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
{
  "success": true
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.
