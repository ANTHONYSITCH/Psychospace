# Contrat API PsychoSpace

Ces documents constituent le contrat officiel entre le frontend, le backend, l'IA et l'IoT. Ils décrivent uniquement les échanges prévus : aucune route n'est implémentée.

Toute modification d'une route ou d'un format doit être validée par l'équipe. Les [contrats de données](../data/) restent la source de vérité des objets métier. Le [schéma SQLite](../../database/schema.sql) décrit leur stockage.

## Conventions communes

- Toutes les routes commencent par `/api`. Les corps utilisent JSON avec `Content-Type: application/json`, sauf les réponses sans corps explicitement indiquées.
- Les paramètres entre accolades sont remplacés par les identifiants réels ; l'utilisateur d'exemple est `ASTRO-001`. Aucun mécanisme d'authentification n'est ajouté à cette étape ; un identifiant fourni ne constitue pas une preuve d'identité.
- Sauf pour la commande de chat et le PATCH documentés, les corps métier reprennent tous les champs requis et non nuls des contrats. Les champs inconnus sont refusés avec `400`. GET, DELETE et les commandes calculate/analyze n'ont pas de corps. Aucun paramètre de requête supplémentaire n'est défini.
- Les dates suivent ISO 8601 en UTC avec suffixe `Z`, par exemple `2026-09-22T18:00:00Z`. L'heure quotidienne du profil utilise `HH:MM:SSZ`. Les producteurs fournissent les dates des objets envoyés ; le backend fournit celles des résultats qu'il génère.
- Les noms de champs sont en anglais. `interests` et `affected_signals` restent des tableaux JSON sur l'API, même s'ils sont sérialisés en TEXT dans SQLite. Les booléens restent `true`/`false`, jamais `0`/`1`.
- `mood`, `stress`, `fatigue`, `energy` et `social_level` sont des entiers de 1 à 10 inclus ; leurs moyennes peuvent être décimales. 1 signifie une humeur très basse ou un niveau très faible et 10 une humeur très positive ou un niveau très élevé. Les durées de sommeil sont en heures et l'activité en minutes, avec décimales autorisées conformément au contrat de données. Aucun arrondi n'est défini par l'API.
- Les historiques renvoient directement un tableau d'objets métier, sans enveloppe ni pagination à ce stade. Un utilisateur existant sans résultats reçoit `200` avec `[]` ; un utilisateur inconnu reçoit `404`. En cas d'égalité des dates, utiliser les identifiants de stockage croissants.
- Les identifiants SQL supplémentaires des check-ins, capteurs et baselines ne sont pas ajoutés aux objets métier retournés. Les créations de check-ins et capteurs renvoient les accusés de réception demandés, avec `checkin_id` ou `sensor_reading_id`. Le profil complet réunit les champs de users et profiles, sans exposer users.created_at.
- Pour le chat, `message` est le champ de commande correspondant à `content` dans l'objet métier. La réponse POST demandée est une projection sans `id` ; l'historique GET contient les objets complets conformes à chat-message.
- PsychoSpace détecte des changements comportementaux par rapport au fonctionnement habituel. Il ne formule jamais de diagnostic médical ou psychiatrique, y compris dans les explications, mémoires et messages de soutien.

## Codes HTTP et erreurs

| Code | Signification |
| --- | --- |
| 200 | Succès d'une lecture, mise à jour, suppression ou commande documentée. |
| 201 | Création réussie, notamment d'une nouvelle baseline. |
| 204 | Analyse de dérive réussie sans événement détecté ; aucun corps. |
| 400 | Données invalides, JSON mal formé, incohérence ou données insuffisantes pour un calcul. |
| 404 | Utilisateur ou ressource introuvable, selon la route. |
| 500 | Erreur interne. |

Les erreurs utilisent la même enveloppe. Exemple de réponse `400` :

```json
{
  "success": false,
  "error": {
    "code": "invalid_data",
    "message": "Les données fournies sont invalides."
  }
}
```

`error.code` vaut `invalid_data` pour 400, `not_found` pour 404 et `internal_error` pour 500. `error.message` fournit une explication lisible sans détails techniques internes. Chaque fiche précise les données attendues, des exemples de requête et réponse et les codes propres à chaque route.

## Routes officielles

| Méthode | Route | Rôle | Documentation |
| --- | --- | --- | --- |
| POST | `/api/checkins` | Enregistrer un élément dans les bilans quotidiens. | [checkins](checkins.md) |
| GET | `/api/checkins/{user_id}` | Retourner l'historique des bilans quotidiens. | [checkins](checkins.md) |
| POST | `/api/sensors` | Enregistrer un élément dans les mesures de capteurs. | [sensors](sensors.md) |
| GET | `/api/sensors/{user_id}` | Retourner l'historique des mesures de capteurs. | [sensors](sensors.md) |
| GET | `/api/profile/{user_id}` | Retourner le profil complet. | [profile](profile.md) |
| PUT | `/api/profile/{user_id}` | Mettre à jour le profil existant. | [profile](profile.md) |
| GET | `/api/baseline/{user_id}` | Retourner la dernière baseline connue. | [baseline](baseline.md) |
| POST | `/api/baseline/{user_id}/calculate` | Calculer une nouvelle baseline et conserver les calculs précédents. | [baseline](baseline.md) |
| GET | `/api/drift/{user_id}` | Retourner les événements de changement comportemental. | [drift](drift.md) |
| POST | `/api/drift/{user_id}/analyze` | Demander au Drift Engine une analyse des données récentes. | [drift](drift.md) |
| POST | `/api/chat` | Envoyer un message et recevoir la réponse de PsychoSpace. | [chat](chat.md) |
| GET | `/api/chat/{user_id}` | Retourner l'historique de conversation. | [chat](chat.md) |
| GET | `/api/memories/{user_id}` | Retourner les mémoires autorisées de l'utilisateur. | [memories](memories.md) |
| POST | `/api/memories` | Créer une mémoire de personnalisation. | [memories](memories.md) |
| PUT | `/api/memories/{memory_id}` | Corriger une mémoire existante. | [memories](memories.md) |
| DELETE | `/api/memories/{memory_id}` | Supprimer une mémoire à la demande de l'utilisateur. | [memories](memories.md) |
| GET | `/api/interventions/{user_id}` | Retourner les propositions de soutien. | [interventions](interventions.md) |
| POST | `/api/interventions` | Créer une proposition de soutien. | [interventions](interventions.md) |
| PATCH | `/api/interventions/{intervention_id}` | Mettre à jour l'acceptation ou la réalisation d'une proposition. | [interventions](interventions.md) |
