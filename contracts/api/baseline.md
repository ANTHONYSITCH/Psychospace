# Contrat API — baseline

Les [conventions communes](README.md) et les [contrats de données](../README.md) s'appliquent à toutes les routes ci-dessous. Documentation uniquement : aucune route n'est implémentée.

## GET /api/baseline/{user_id}

Retourner la dernière baseline connue.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Objet [baseline](../data/baseline.example.json) ayant le calculated_at le plus récent ; à égalité, plus grand id SQL. Aucun id SQL dans la réponse.

### Exemple de requête

```http
GET /api/baseline/ASTRO-001 HTTP/1.1
```

### Exemple de réponse — 200

```json
{
  "user_id": "ASTRO-001",
  "calculated_at": "2026-09-22T00:00:00Z",
  "sleep_hours_avg": 7.4,
  "mood_avg": 7.2,
  "stress_avg": 3.5,
  "fatigue_avg": 3.8,
  "energy_avg": 7,
  "social_level_avg": 6.5,
  "activity_minutes_avg": 45,
  "observation_days": 14
}
```

**Codes HTTP :** 200 : succès. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 404 également si aucune baseline n'existe.

## POST /api/baseline/{user_id}/calculate

Calculer une nouvelle baseline et conserver les calculs précédents.

**Données attendues et résultat :** user_id dans le chemin ; aucun corps. Calcul synchrone sur les données disponibles. Réponse conforme au contrat baseline : moyennes des indicateurs entre 1 et 10, sommeil en heures, activité en minutes et observation_days entier positif. La méthode de calcul et les données minimales restent à définir en équipe.

### Exemple de requête

```http
POST /api/baseline/ASTRO-001/calculate HTTP/1.1
```

### Exemple de réponse — 201

```json
{
  "user_id": "ASTRO-001",
  "calculated_at": "2026-09-22T00:00:00Z",
  "sleep_hours_avg": 7.4,
  "mood_avg": 7.2,
  "stress_avg": 3.5,
  "fatigue_avg": 3.8,
  "energy_avg": 7,
  "social_level_avg": 6.5,
  "activity_minutes_avg": 45,
  "observation_days": 14
}
```

**Codes HTTP :** 201 : création réussie. 400 : données ou paramètres invalides. 404 : utilisateur ou ressource introuvable. 500 : erreur interne. 400 également si les données sont insuffisantes.
