# Contrat API — chat

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## POST /api/chat

Envoyer un message et recevoir la réponse de PsychoSpace.

**Données attendues et résultat :** Corps : user_id et message, chaînes non vides. message est le champ de commande demandé, correspondant à content dans l'historique. La réponse courte omet volontairement id ; les deux messages complets, avec id généré, apparaissent dans l'historique GET. role vaut assistant dans la réponse.

### Exemple de requête

```http
POST /api/chat HTTP/1.1
Content-Type: application/json

{
  "user_id": "ASTRO-001",
  "message": "Ça va, je suis juste fatigué."
}
```

### Exemple de réponse — 200

```json
{
  "user_id": "ASTRO-001",
  "role": "assistant",
  "content": "Souhaites-tu me parler de ta journée ?",
  "timestamp": "2026-09-22T19:05:00Z"
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.

## GET /api/chat/{user_id}

Retourner l'historique de conversation.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Tableau de messages complets [chat-message](../data/chat-message.example.json) avec id, user_id, role, content, timestamp, triés par timestamp croissant. role accepte uniquement user ou assistant.

### Exemple de requête

```http
GET /api/chat/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
[
  {
    "id": "MSG-001",
    "user_id": "ASTRO-001",
    "role": "user",
    "content": "Écouter de la musique m'aide quand je suis stressé.",
    "timestamp": "2026-09-21T18:59:00Z"
  }
]
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne.
