# Backend PsychoSpace V0.1

API locale : `GET /health`, `GET /api/profile/{user_id}`, `POST /api/checkins`, `GET /api/checkins/{user_id}`, `POST /api/sensors` et `GET /api/sensors/{user_id}`. Les routes lisent et écrivent dans SQLite. Le profil reconvertit `interests` en tableau JSON. Un utilisateur ou profil absent renvoie 404 dans l'enveloppe d'erreur du contrat API. Les erreurs internes renvoient un message générique ; leurs détails restent dans les logs du serveur.

## Installation et lancement

Depuis la racine du projet, avec Python 3.11 ou supérieur (tests exécutés avec Python 3.14) :

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Si PowerShell bloque l'activation, utiliser directement l'interpréteur sans modifier sa politique d'exécution :

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Sous Linux/macOS, activer l'environnement avec `source backend/.venv/bin/activate`. Les commandes `python -m ...` restent les mêmes. Le serveur écoute par défaut sur `127.0.0.1:8000`.

Les dépendances directes sont FastAPI, Uvicorn, Pydantic (validation des données) et HTTPX (TestClient). SQLite et unittest font partie de Python. L'API fonctionne hors ligne une fois les dépendances installées ; l'interface Swagger standard `/docs` peut charger ses assets depuis un CDN, mais les endpoints n'en dépendent pas.

## Configuration et initialisation

Les chemins sont déterminés par `pathlib` depuis `config.py`, indépendamment du dossier courant. La base par défaut est `database/psychospace.db`, déjà ignorée par le `.gitignore` commun. L'import Python seul ne crée pas la base : l'initialisation a lieu au démarrage de FastAPI.

La variable facultative `PSYCHOSPACE_DB_PATH` permet de choisir un autre fichier. Un chemin relatif est résolu depuis la racine du projet. `DATABASE_URL` et les fichiers `.env` ne sont pas interprétés dans cette version ; le point de configuration est centralisé pour une évolution ultérieure.

Le vrai fichier `database/schema.sql` est lu et exécuté sans modification. Il contient sa propre transaction et n'est pas idempotent. Sur une base vide, il est exécuté directement. Sur une base existante, les définitions SQL des tables et index sont comparées à celles obtenues en exécutant le schéma officiel en mémoire. Si elles correspondent, aucune table n'est recréée. Un schéma partiel ou différent provoque un arrêt explicite sans suppression ni migration automatique. Cette comparaison est volontairement stricte : une structure équivalente écrite différemment peut demander une vérification manuelle.

Chaque connexion active les clés étrangères, valide ou annule sa transaction et se ferme à la sortie de son contexte. Cette V0.1 vise un seul processus serveur ; les initialisations concurrentes d'une base neuve ne sont pas prises en charge.

## Seed ASTRO-001

Sur une base sans utilisateur, les sept fichiers JSON réels de `database/seeds/` sont importés dans une transaction unique :

| Table | Lignes importées |
| --- | --- |
| users | 1 |
| profiles | 1 |
| daily_checkins | 15 |
| sensor_readings | 90 |
| memories | 6 |
| baselines | 1 |
| drift_events | 2 |
| interventions | 4 |
| chat_messages | 0 |

Si un utilisateur existe déjà, notamment ASTRO-001, le chargement est ignoré : aucun doublon, remplacement ou rétablissement automatique de données supprimées. Le contrôle et les insertions sont protégés par `BEGIN IMMEDIATE`. Une erreur annule tout l'import ; le démarrage échoue clairement et peut être relancé après correction de sa cause.

Les listes `interests` et `affected_signals` sont sérialisées en TEXT. Les booléens des interventions sont enregistrés par sqlite3 en 0/1. Les identifiants numériques sont attribués par SQLite. `users.created_at`, absent du profil JSON mais requis par le schéma, est la date technique d'import UTC ; il n'est pas ajouté à la réponse API. Les autres dates du dataset sont préservées.

## Écarts et limites connus des fichiers communs

- Le profil est réparti entre `users` et `profiles` ; la jointure reconstitue exactement l'objet API.
- Les durées d'activité décimales sont autorisées par les contrats, alors que `daily_checkins.activity_minutes` est déclaré INTEGER. SQLite utilise une affinité de type sans mode STRICT dans ce schéma : les nouvelles valeurs décimales sont conservées sans arrondi, ce qui est vérifié par les tests. Le schéma reste inchangé.
- Plusieurs colonnes SQLite sont facultatives, contrairement aux objets métier requis. La réponse de profil est validée : une valeur manquante ou des intérêts mal formés produisent une erreur interne générique, plutôt qu'un objet incompatible.
- Les valeurs du profil d'exemple des contrats diffèrent du dataset (mission, préférences). Les champs concordent ; cette route retourne les valeurs réelles du dataset, comme demandé.

Aucun fichier commun n'est corrigé ni modifié par le backend. Aucune incohérence bloquante n'empêche l'import du dataset actuel.

## Tests et vérification manuelle

Depuis la racine, environnement activé :

```powershell
python -m unittest discover -s backend/tests -v
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/profile/ASTRO-001
```

Les tests utilisent des bases temporaires supprimées ensuite, sans toucher à la base de développement. Ils vérifient les endpoints, le profil exact, les données importées, les clés étrangères, les redémarrages sans doublons, la préservation des modifications, les requêtes paramétrées, les erreurs sans détails internes et l'annulation d'un import incomplet.

La création de l'application utilise le [cycle de vie FastAPI](https://fastapi.tiangolo.com/advanced/events/) et les tests utilisent [TestClient](https://fastapi.tiangolo.com/tutorial/testing/) dans un contexte pour déclencher le démarrage.

## Check-ins et capteurs dans Swagger

Après lancement du serveur, ouvrir http://127.0.0.1:8000/docs. Déplier la route POST, cliquer sur **Try it out**, coller le JSON puis cliquer sur **Execute**. Ces actions enregistrent réellement les données dans la base utilisée par le serveur.

Pour `POST /api/checkins` :

```json
{
  "user_id": "ASTRO-001",
  "timestamp": "2080-04-16T18:00:00Z",
  "sleep_hours": 6.5,
  "mood": 6,
  "stress": 5,
  "fatigue": 6,
  "energy": 5,
  "social_level": 4,
  "activity_minutes": 22.5
}
```

Réponse 201 : `{"success": true, "checkin_id": 16}` sur une base contenant uniquement les seeds.

Pour `POST /api/sensors` :

```json
{
  "user_id": "ASTRO-001",
  "sensor_type": "heart_rate",
  "value": 72,
  "unit": "bpm",
  "timestamp": "2080-04-16T17:00:00Z"
}
```

Réponse 201 : `{"success": true, "sensor_reading_id": 91}` sur une base contenant uniquement les seeds. Pour tester movement, utiliser `sensor_type: "movement"`, `value: 0.7`, `unit: "m/s²"`. D'autres types, par exemple temperature avec une unité explicite, sont acceptés. Les trois types déjà convenus contrôlent leur unité : heart_rate/bpm, spo2/%, movement/m/s².

Utiliser ensuite les routes GET correspondantes avec `user_id = ASTRO-001`. Les réponses sont des tableaux d'objets métier sans identifiant SQL, triés chronologiquement et par identifiant d'insertion à dates égales. Un utilisateur existant sans mesures reçoit `[]` ; un utilisateur inconnu reçoit 404. Chaque POST crée une mesure supplémentaire, même si le corps est identique à un envoi précédent.

Les champs sont tous requis ; les champs supplémentaires, nombres sous forme de chaînes, booléens à la place des nombres et valeurs non finies sont refusés. Les cinq scores sont des entiers de 1 à 10 ; sommeil et activité sont positifs ou nuls. Les dates sont des chaînes ISO 8601 UTC terminées par `Z`, avec secondes et éventuellement 1 à 6 décimales. Les champs de capteur et les identifiants ne peuvent pas être vides.

Une validation incorrecte renvoie **400**, avec `success: false` et `error.code: "invalid_data"`, conformément au contrat. Les tests supplémentaires couvrent ces cas, les nouveaux types de capteur, le tri, la séparation des utilisateurs et la persistance réelle dans des bases SQLite temporaires. Ils ne modifient pas la base de développement ni les seeds communs.
