# Base de données PsychoSpace

`schema.sql` définit les neuf tables du prototype SQLite, sans données initiales. Aucun fichier `.db` n'est fourni. Les contrats de référence restent dans `../contracts/data/` ; leurs noms de champs sont conservés.

## Pourquoi SQLite ?

SQLite permet un prototype local avec un stockage relationnel, des transactions et des clés étrangères, sans serveur de base de données à administrer. Cela simplifie le workshop et convient à une utilisation locale embarquée. Le choix pourra être réévalué si le projet nécessite de nombreux accès concurrents.

## Tables et relations

| Table | Rôle et relation |
| --- | --- |
| `users` | Identité et mission de l'astronaute ; parent des huit autres tables via `user_id`. |
| `profiles` | Préférences et habitudes ; zéro ou un profil par utilisateur, grâce à `user_id` comme clé primaire et étrangère. |
| `daily_checkins` | Bilans quotidiens ; plusieurs bilans possibles par utilisateur. |
| `sensor_readings` | Mesures IoT ; plusieurs mesures possibles par utilisateur. |
| `memories` | Informations de personnalisation ; plusieurs mémoires par utilisateur. |
| `baselines` | Références personnelles ; plusieurs calculs conservés par utilisateur, distingués par `id` et datés par `calculated_at`. |
| `drift_events` | Événements de changement comportemental ; plusieurs événements par utilisateur. |
| `interventions` | Propositions de soutien ; plusieurs propositions par utilisateur, chacune pouvant référencer un événement via `drift_event_id`. Un événement peut avoir plusieurs propositions. |
| `chat_messages` | Historique des messages ; plusieurs messages par utilisateur, de rôle `user` ou `assistant`. |

Le contrat de profil se reconstitue en joignant `users` et `profiles` sur `user_id`. `users.created_at` et les identifiants numériques des bilans, mesures et baselines sont des métadonnées de stockage supplémentaires demandées pour ce schéma.

Les clés étrangères sont activées par `PRAGMA foreign_keys = ON` avant la transaction de création. Ce réglage doit être activé sur **chaque connexion SQLite**, avant toute transaction. Les suppressions ou modifications de clés référencées sont bloquées tant que des lignes dépendantes existent ; aucune cascade n'est définie.

Les deux clés étrangères d'`interventions` vérifient l'existence de l'utilisateur et de l'événement. La vérification que cet événement appartient au même utilisateur reste à assurer lors de la validation des données.

## Stockage et correspondance avec les contrats

- Les dates (`created_at`, `timestamp`, `calculated_at`, `detected_at`) sont stockées en `TEXT` au format ISO 8601, en UTC : `YYYY-MM-DDTHH:MM:SSZ`. `preferred_contact_time` conserve une heure quotidienne UTC au format `HH:MM:SSZ`. Le schéma ne valide pas leur format ; les composants producteurs devront le respecter.
- `interests` et `affected_signals` contiennent des tableaux de chaînes JSON sérialisés dans `TEXT`. Les composants doivent sérialiser ces listes à l'écriture et les désérialiser à la lecture, sans changer les noms de champs. Le schéma ne valide pas le contenu JSON.
- Les durées de sommeil sont en heures ; les durées d'activité sont en minutes. Les cinq indicateurs `mood`, `stress`, `fatigue`, `energy` et `social_level` ont des contraintes `CHECK` de 1 à 10 inclus. Leurs moyennes sont stockées en `REAL`.
- `activity_minutes` est déclaré `INTEGER` conformément à la demande de schéma. La documentation des contrats autorise aussi des durées décimales : SQLite sans mode `STRICT` peut conserver une valeur décimale dans cette colonne. Aucun arrondi implicite ne doit être ajouté par les composants ; une exigence future de minutes entières devra être validée en équipe.
- `accepted` et `completed` utilisent `0` pour `false` et `1` pour `true`, avec des contraintes `CHECK`. Une réalisation confirmée doit correspondre à une acceptation confirmée ; cette cohérence reste à valider par les composants.
- Les colonnes sans `NOT NULL` suivent la nullabilité demandée pour le stockage. Les objets échangés doivent néanmoins respecter les champs requis et non nuls des contrats. Les contraintes SQL ne remplacent pas la validation complète des contrats, notamment des types entiers, des vocabulaires et des autres bornes numériques.

## Capteurs génériques

`sensor_readings` conserve une valeur numérique scalaire, un `sensor_type`, une `unit` et un `timestamp`. Aucun catalogue fermé de capteurs n'est imposé : `heart_rate` (bpm), `spo2` (%) et `movement` (m/s² selon le contrat) utilisent la même structure. De futurs capteurs pourront être ajoutés en convenant de leur type, de leur signification et de leur unité, sans ajouter de colonne.

## Index

Les index composés `(user_id, timestamp)` accélèrent les historiques de bilans, de mesures et de messages par utilisateur et par période. Les mémoires, baselines, événements et interventions disposent d'index équivalents sur leur champ de date. Leur première colonne couvre aussi les recherches par `user_id`, sans index simple redondant. Un index sur `interventions.drift_event_id` facilite la recherche des propositions associées à un événement. Les clés primaires de `users` et `profiles` indexent déjà `user_id`.

## Portée des événements

`drift_events` représente une dérive comportementale par rapport aux habitudes personnelles, jamais un diagnostic médical ou psychiatrique. `explanation` décrit uniquement les changements observés ; les scores et niveaux ne représentent pas une gravité clinique. Cette règle s'applique aussi aux textes produits par les autres briques.
