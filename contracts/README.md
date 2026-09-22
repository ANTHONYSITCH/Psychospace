# Contrats de données PsychoSpace

Ces fichiers définissent le contrat commun entre le frontend, le backend, l'IA, la base de données et l'IoT. Ils présentent des exemples JSON de référence, sans implémentation ni schéma de validation exécutable. L'utilisateur d'exemple est `ASTRO-001` (Alex).

Les noms de champs ne doivent pas être modifiés individuellement sans validation de l'équipe. Toute évolution des types, unités ou valeurs convenues doit également être coordonnée entre les briques.

PsychoSpace détecte des changements comportementaux mais ne pose pas de diagnostic médical ou psychiatrique. Les événements décrivent uniquement des écarts observés par rapport aux habitudes personnelles.

## Conventions communes

- Tous les champs présentés sont requis et non nuls dans ces contrats de prototype.
- Les identifiants et les valeurs textuelles sont des chaînes JSON ; les listes sont des tableaux de chaînes ; les nombres et booléens utilisent leurs types JSON natifs.
- Les dates et heures complètes suivent ISO 8601 en UTC : `2026-09-22T18:00:00Z`. Le suffixe `Z` signifie UTC.
- Les durées de sommeil sont exprimées en heures, les durées d'activité en minutes. Elles peuvent être décimales et sont positives ou nulles.
- `mood`, `stress`, `fatigue`, `energy` et `social_level` sont des entiers de 1 à 10 inclus. Pour `mood`, 1 signifie une humeur très basse et 10 une humeur très positive ; pour les autres, 1 signifie un niveau très faible et 10 un niveau très élevé. `social_level` décrit le niveau d'interactions sociales perçu.
- Les moyennes de ces cinq indicateurs restent sur l'échelle de 1 à 10 et peuvent être décimales. Un score élevé de stress ou de fatigue correspond donc à davantage de stress ou de fatigue.
- Les valeurs d'exemple ne définissent aucun seuil de détection ni algorithme.

## Profil — `data/profile.example.json`

Décrit l'astronaute, sa mission et ses préférences de soutien.

| Champ | Type et signification |
| --- | --- |
| `user_id` | Chaîne, identifiant commun de l'astronaute. |
| `first_name` | Chaîne, prénom. |
| `age` | Entier positif, âge en années. |
| `mission_id` | Chaîne, identifiant de mission. |
| `normal_sleep_hours` | Nombre, durée habituelle de sommeil en heures par jour. |
| `preferred_support` | Chaîne, préférence de soutien ; `music` est un exemple, pas une liste exhaustive. |
| `preferred_contact_time` | Chaîne, heure quotidienne ISO 8601 en UTC, ici `19:00:00Z`. |
| `interests` | Tableau de chaînes, centres d'intérêt. |

## Bilan quotidien — `data/daily-checkin.example.json`

Recueille les observations déclarées par l'astronaute pour la journée.

| Champ | Type et signification |
| --- | --- |
| `user_id` | Chaîne, identifiant de l'astronaute. |
| `timestamp` | Chaîne, date et heure du bilan en UTC. |
| `sleep_hours` | Nombre, heures de sommeil de la dernière période de sommeil. |
| `mood` | Entier, humeur de 1 à 10. |
| `stress` | Entier, stress de 1 à 10. |
| `fatigue` | Entier, fatigue de 1 à 10. |
| `energy` | Entier, énergie de 1 à 10. |
| `social_level` | Entier, niveau d'interactions sociales perçu de 1 à 10. |
| `activity_minutes` | Nombre, minutes d'activité physique de la journée. |

## Mesure de capteur — `data/sensor-reading.example.json`

Transporte une mesure numérique générique issue de l'IoT.

| Champ | Type et signification |
| --- | --- |
| `user_id` | Chaîne, identifiant de l'astronaute. |
| `sensor_type` | Chaîne, type de mesure extensible. |
| `value` | Nombre, valeur dans l'unité indiquée. |
| `unit` | Chaîne, unité explicite de la mesure. |
| `timestamp` | Chaîne, date et heure d'acquisition en UTC. |

Exemples de couples : `heart_rate` / `bpm` (battements par minute), `spo2` / `%` (saturation en oxygène), `movement` / `m/s²` (amplitude d'accélération). D'autres capteurs peuvent utiliser la même structure ; leur signification et leur unité doivent être convenues par l'équipe. Une mesure représente une valeur scalaire, pas un vecteur ou une série.

## Mémoire — `data/memory.example.json`

Conserve une information utile à la personnalisation du soutien.

| Champ | Type et signification |
| --- | --- |
| `id` | Chaîne, identifiant unique de la mémoire. |
| `user_id` | Chaîne, identifiant de l'astronaute. |
| `category` | Chaîne, catégorie ; ici `support_preference`. |
| `content` | Chaîne, information mémorisée en langage naturel. |
| `importance` | Entier de 1 à 10, de peu important à très important pour la personnalisation. |
| `source` | Chaîne, origine de l'information ; ici `user_chat` pour une déclaration dans le chat. |
| `created_at` | Chaîne, date et heure de création en UTC. |

`category` et `source` sont des vocabulaires extensibles à coordonner avec l'équipe.

## Référence personnelle — `data/baseline.example.json`

Décrit les moyennes individuelles utilisées pour comparer les observations ultérieures.

| Champ | Type et signification |
| --- | --- |
| `user_id` | Chaîne, identifiant de l'astronaute. |
| `calculated_at` | Chaîne, date et heure du calcul en UTC. |
| `sleep_hours_avg` | Nombre, sommeil moyen en heures par jour. |
| `mood_avg` | Nombre, humeur moyenne de 1 à 10. |
| `stress_avg` | Nombre, stress moyen de 1 à 10. |
| `fatigue_avg` | Nombre, fatigue moyenne de 1 à 10. |
| `energy_avg` | Nombre, énergie moyenne de 1 à 10. |
| `social_level_avg` | Nombre, niveau social moyen de 1 à 10. |
| `activity_minutes_avg` | Nombre, activité physique moyenne en minutes par jour. |
| `observation_days` | Entier strictement positif, nombre de jours observés ayant contribué aux moyennes. |

L'exemple représente les 14 jours précédant le bilan du 22 septembre. La méthode de calcul et la gestion des jours manquants restent à définir collectivement.

## Événement de changement — `data/drift-event.example.json`

Décrit un écart comportemental par rapport à la référence personnelle, sans diagnostic médical ou psychiatrique, y compris dans le texte libre.

| Champ | Type et signification |
| --- | --- |
| `id` | Chaîne, identifiant unique de l'événement. |
| `user_id` | Chaîne, identifiant de l'astronaute. |
| `detected_at` | Chaîne, date et heure de détection en UTC. |
| `level` | Chaîne parmi `low`, `moderate`, `high` : ampleur du changement, sans gravité clinique. |
| `drift_score` | Nombre sans unité de 0 à 1 inclus ; une valeur élevée indique un écart plus marqué. |
| `confidence` | Nombre sans unité de 0 à 1 inclus ; confiance estimée dans la détection, sans interprétation en probabilité médicale. |
| `affected_signals` | Tableau de chaînes, noms des indicateurs concernés, ici des champs du bilan quotidien ; pour un capteur, utiliser le `sensor_type` convenu. |
| `explanation` | Chaîne, description factuelle des changements observés. |
| `status` | Chaîne parmi `open`, `acknowledged`, `resolved` : événement ouvert, pris en compte ou clos. |

Les scores sont illustratifs. Les seuils reliant `drift_score` à `level` restent à définir.

## Proposition de soutien — `data/intervention.example.json`

Relie une proposition de soutien à un événement et suit son acceptation et son achèvement.

| Champ | Type et signification |
| --- | --- |
| `id` | Chaîne, identifiant unique de la proposition. |
| `user_id` | Chaîne, identifiant de l'astronaute. |
| `drift_event_id` | Chaîne, référence à l'`id` d'un événement du même utilisateur. |
| `created_at` | Chaîne, date et heure de création en UTC. |
| `type` | Chaîne, type de soutien ; ici `music_break`, pause musicale. Vocabulaire extensible en équipe. |
| `message` | Chaîne, proposition présentée à l'astronaute. |
| `accepted` | Booléen, `true` si l'acceptation est confirmée. `false` signifie qu'aucune acceptation n'est confirmée et ne distingue pas attente et refus. |
| `completed` | Booléen, `true` si la réalisation est confirmée ; sinon `false`. Une proposition terminée doit avoir été acceptée. |

## Message de chat — `data/chat-message.example.json`

Représente un message de la conversation entre l'astronaute et l'assistant.

| Champ | Type et signification |
| --- | --- |
| `id` | Chaîne, identifiant unique du message. |
| `user_id` | Chaîne, identifiant de l'astronaute auquel appartient la conversation, même pour un message de l'assistant. |
| `role` | Chaîne, uniquement `user` ou `assistant`. |
| `content` | Chaîne, texte du message. |
| `timestamp` | Chaîne, date et heure du message en UTC. |
