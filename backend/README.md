# Backend PsychoSpace V0.1

## PsychoSpace Companion

`POST /api/chat` reçoit `user_id` et `message` (chaînes non vides) et retourne
`user_id`, `role: "assistant"`, `content`, `timestamp` avec 200.
`GET /api/chat/{user_id}` retourne les messages complets avec leur `id`, en ordre
chronologique ; `[]` sans historique, 404 pour un utilisateur inconnu, 400 pour
des données invalides. Exemple de corps :

```json
{"user_id": "ASTRO-001", "message": "Ça va, je suis juste fatigué."}
```

Ollama formule la réponse ; le Drift Engine reste seul responsable de
`drift_score`, `level`, `affected_signals`, `explanation`. Le chat ne déclenche
aucun recalcul, diagnostic ni intervention.

```text
Check-ins + Sensors
        ↓
SQLite
        ↓
Baseline + Drift Engine
        ↓
Profile + Memories + Context
        ↓
Ollama
        ↓
Human-centered response
```

Configurer `OLLAMA_URL` (défaut `http://localhost:11434`) et `OLLAMA_MODEL`
(obligatoire, nom du modèle déjà installé localement). Le démarrage charge ces
clés et les trois paramètres suivants depuis `.env.local` ; les variables du processus ont
priorité. Aucun nom de modèle n'est codé dans la logique métier. L'ancien
`OLLAMA_BASE_URL` du fichier d'exemple n'est pas utilisé par le compagnon.

| Paramètre | Défaut | Utilisation |
| --- | --- | --- |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Délai HTTP en secondes, strictement positif ; connexion plafonnée à 5 s. |
| `OLLAMA_NUM_PREDICT` | `160` | Maximum de tokens générés, entier positif. |
| `OLLAMA_TEMPERATURE` | `0.3` | Température entre 0 et 2. |

La fenêtre du modèle reste à 8 192 tokens. Le prompt demande 2 à 4 phrases,
une seule proposition d'action principale et éventuellement une question courte.
Le modèle n'est jamais remplacé automatiquement.

Le client utilise HTTPX, déjà présent, et l'[API chat native Ollama](https://docs.ollama.com/api/chat)
avec `stream: false`. Il accepte uniquement une adresse HTTP de boucle locale,
ignore les proxies et refuse les redirections. Il vérifie `/api/show` avant
chaque génération et refuse les modèles distants/cloud. Aucun téléchargement
automatique, SDK cloud ou fallback distant. Sur le serveur Ollama, activer aussi
`OLLAMA_NO_CLOUD=1` avant son lancement pour désactiver ses fonctions cloud
([documentation Ollama](https://docs.ollama.com/faq)). Le modèle doit déjà être
téléchargé pour fonctionner hors ligne.

Le Context Builder lit uniquement SQLite pendant les requêtes : prénom et
préférences, indicateurs principaux de la dernière baseline, dernier événement
de dérive, trois derniers check-ins, jusqu'à douze mémoires prioritaires et six
derniers messages. La sélection du drift trie `detected_at` par secondes puis
fraction UTC décroissantes, et `id DESC` à date égale, avec `LIMIT 1` : ni ordre
d'insertion, ni lecture des seeds, ni recalcul. L'id et la date sont disponibles
pour vérifier la sélection mais ne sont pas envoyés au modèle. Le contexte envoyé
omet âge, mission, métadonnées, timestamps et capteurs bruts. Les check-ins sont
compactés en colonnes/lignes ; les mémoires gardent leur contenu sans métadonnées.
L'explication conserve un extrait exact de 300 caractères maximum, marqué comme
extrait si tronqué ; le texte complet du moteur reste inchangé dans SQLite.
Le message courant est ajouté séparément, une seule fois.
Les données absentes restent nulles ou vides, sans invention. Les mémoires du
Memory Vault sont considérées comme autorisées en V0.1 ; seules celles de
l'utilisateur sont transmises. Une mémoire supprimée n'est plus dans ce contexte.
Le prompt interdit de réutiliser un souvenir absent du Vault, même si l'ancien
historique le mentionne. Aucune conversation ne crée automatiquement de mémoire.

La lecture SQLite matérialise toutes les lignes puis ferme complètement la
connexion. Le contexte est assemblé en mémoire et Ollama est appelé sans aucune
connexion ni transaction SQLite maintenue par la requête. Après génération, une
nouvelle connexion ouvre une transaction courte `BEGIN IMMEDIATE` et insère les
deux messages. Une erreur d'insertion annule les deux ; un échec Ollama n'enregistre
aucun message. Les échanges antérieurs restent intacts. Ollama indisponible, modèle absent, timeout ou
réponse invalide donnent **503**, extension demandée mais non mentionnée dans
le contrat partagé inchangé. Le contexte est un instantané avant génération : les
modifications concurrentes ne seront visibles qu'à la prochaine requête.

Le logger `backend.app.services.ollama_client` émet au niveau INFO
`Ollama generation completed in X.XX seconds`. La mesure couvre uniquement
`POST /api/chat` vers Ollama et la validation de sa réponse, pas SQLite ni la
vérification préalable `/api/show`. Aucun contenu privé ni prompt n'est loggé.
Le premier appel peut charger le modèle ; le second bénéficie du modèle déjà en
mémoire. Un poste lent peut nécessiter une valeur explicite supérieure à 60 s
pour `OLLAMA_TIMEOUT_SECONDS`. Si les appels restent au-dessus de 30 s, le goulot
est probablement l'inférence locale du modèle sur le matériel, et non SQLite.

Mesure locale du 23 septembre 2026, deux POST HTTP consécutifs vers FastAPI avec
le modèle inchangé `qwen3:4b-instruct-2507-q4_K_M` : **243,33 s** pour le premier
appel (chargement initial inclus), **21,60 s** pour le second. Les deux ont renvoyé
200 ; quatre messages ont été ajoutés atomiquement, sans modification des mémoires.
Le prompt du premier appel comptait 898 tokens, contre 1 315 lors de l'ancien essai
(historiques différents : cette comparaison n'isole pas le gain de latence).
Le processus de mesure utilisait `OLLAMA_TIMEOUT_SECONDS=300` pour permettre le
chargement à froid ; le défaut applicatif reste 60 s et `.env.local` est inchangé.
Sur ce poste, configurer explicitement 300 s pour les démarrages à froid : le défaut
de 60 s peut produire un 503 avant la fin du chargement. Le coût initial reste
principalement celui d'Ollama et du matériel ; le second appel mesuré est sous 30 s.
Un verrou d'écriture SQLite indépendant a été obtenu immédiatement pendant la
génération réelle, puis annulé sans changement de données.

Le prompt sépare FACTS et INFERENCES, impose des réponses brèves, sans diagnostic,
sans invention de souvenirs et sans simulation de proches. Ces instructions ne
garantissent pas toutes les sorties d'un modèle génératif. Les événements seed
de 2080 sont fictifs et peuvent être décalés de l'horloge réelle ; le dernier
événement enregistré ne prouve pas un état actuel. Aucune authentification n'est
ajoutée dans cette V0.1. Les tests automatiques utilisent des bases temporaires et
un faux Ollama, sans dépendre du modèle installé :

```powershell
python -m unittest discover -s backend/tests -v
python -m unittest discover -s ai/tests -v
```

API locale : santé, profil, check-ins, capteurs, baseline, analyse de dérive et Memory Vault. Toutes les routes disponibles sont visibles dans Swagger. Les routes lisent et écrivent dans SQLite. Le profil reconvertit `interests` en tableau JSON. Un utilisateur ou profil absent renvoie 404 dans l'enveloppe d'erreur du contrat API. Les erreurs internes renvoient un message générique ; leurs détails restent dans les logs du serveur.

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

La variable facultative `PSYCHOSPACE_DB_PATH` permet de choisir un autre fichier. Un chemin relatif est résolu depuis la racine du projet. `DATABASE_URL` et `.env` ne sont pas interprétés ; seules les cinq variables Ollama documentées de `.env.local` sont chargées au démarrage.

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

## AI Integration

Flux : **Check-ins + Sensors → SQLite → Baseline Engine → Drift Engine → adaptation → SQLite → FastAPI**. Le service `app/services/ai_service.py` transmet les lignes SQL aux fonctions existantes de `ai/core/`, sans dupliquer leurs formules ni lire les seeds pendant les requêtes. Les seeds restent réservés à l'initialisation. Aucune dépendance supplémentaire n'est nécessaire ; lancer le serveur depuis la racine permet d'importer `ai`.

| Route | Comportement |
| --- | --- |
| `POST /api/baseline/{user_id}/calculate` | Calcule sur les sept premiers jours via le moteur IA, conserve les anciennes baselines et retourne la nouvelle avec 201. |
| `GET /api/baseline/{user_id}` | Lit la baseline la plus récente selon calculated_at, puis id SQL à égalité. Aucun calcul implicite. 404 si absente. |
| `POST /api/drift/{user_id}/analyze` | Analyse les trois derniers jours calendaires via le moteur, enregistre un événement et le retourne avec 200 si le niveau interne n'est pas stable. Sinon 204 sans corps ni nouvel événement. |
| `GET /api/drift/{user_id}` | Lit l'historique chronologique ; désérialise affected_signals en tableau JSON. Tableau vide si aucun événement. |

Un utilisateur absent renvoie 404. Des données insuffisantes, incomplètes ou incompatibles (dont plusieurs check-ins le même jour, non pris en charge par le moteur actuel) renvoient 400. Une baseline manquante lors de l'analyse renvoie 400 en demandant de la calculer au préalable. Une exception inattendue du moteur renvoie 500 sans détail interne. Les GET ne modifient rien. Les POST enregistrent leur résultat dans une transaction ; les check-ins et mesures restent inchangés. Une nouvelle demande explicite d'analyse peut créer un nouvel événement pour la même fenêtre : aucune déduplication n'est introduite.

Le service fournit l'historique SQL nécessaire à la référence et aux capteurs ; le moteur sélectionne lui-même la fenêtre récente. Une fenêtre de trois jours partiellement renseignée reste analysable selon la règle de confiance du moteur, si les jours de référence sont disponibles. Il n'y a ni imputation ni recalcul silencieux de la baseline.

### Adaptations explicites aux contrats

- Le moteur calcule sur **0–100** ; `drift_score` de l'API est divisé par 100, car le contrat officiel exige **0–1**. Ainsi 94,75 devient 0,9475.
- `mild` devient `low` ; `moderate` et `high` restent identiques. `stable` produit 204, conformément au contrat API, sans événement artificiel.
- `affected_signals` devient la liste des noms des signaux. La liste est sérialisée en TEXT dans SQLite, puis restaurée à la lecture. Les détails par signal, `recent_window_days` et `sensor_context` restent internes : les contrats et le schéma ne prévoient pas ces champs. Le moteur reçoit bien movement, heart_rate et spo2 ; aucun de ces capteurs ne modifie son score.
- Un événement reçoit un identifiant UUID préfixé `DRIFT-`, un `detected_at` UTC et `status: "open"`. L'explication descriptive du moteur est conservée sans interprétation médicale.

### Dates et référence du prototype

Le moteur utilise `calculated_at` comme **fin des données de référence**, alors que l'API stocke une **date de calcul**. Le service adapte uniquement ce champ dans la copie transmise au moteur : timestamp du dernier des `observation_days` premiers check-ins. Les moyennes enregistrées restent inchangées. Cette convention s'applique au prototype fondé sur les premiers jours ; la provenance des fenêtres devra être précisée avant d'utiliser d'autres stratégies de baseline.

Le dataset fictif est daté de 2080, après l'horloge réelle du poste. Pour que la nouvelle baseline soit effectivement la plus récente, les dates enregistrées utilisent une horloge logique UTC : maximum entre l'heure réelle et les dates pertinentes (fin de référence ou dernières observations, dernier résultat enregistré), ces dernières étant avancées d'une microseconde. En démonstration, cela produit des dates simulées de 2080, **pas des heures réelles d'exécution**. Avec des données passées et une horloge à jour, l'heure réelle prévaut. Cette adaptation conserve le tri officiel par date sans modifier les seeds. Aucun changement n'est apporté au moteur.

Dans Swagger, exécuter sans corps, avec `user_id = ASTRO-001`, successivement le POST baseline, le GET baseline, le POST drift puis le GET drift. Sur le dataset intact : observation_days = 7, score interne final 94,75/100, score API 0,9475 et niveau high. L'historique contient aussi les deux événements illustratifs préchargés, qui n'ont pas été calculés par ce moteur.

Tests d'intégration et tests IA, depuis la racine :

```powershell
python -m unittest discover -s backend/tests -v
python -m unittest discover -s ai/tests -v
```

Les tests bloquent les lectures de fichiers pendant certaines requêtes et modifient uniquement une base temporaire pour prouver que les résultats viennent de SQLite. Ils vérifient aussi la persistance, le traitement stable sans événement, la conservation des entrées et les erreurs du moteur.

## Memory Vault

Le Memory Vault conserve les informations de personnalisation explicitement autorisées par l'astronaute. Pour cette V0.1, les mémoires présentes dans SQLite sont considérées comme autorisées, y compris les six mémoires initiales du dataset.

"PsychoSpace uses only memories explicitly stored and visible to the astronaut. The astronaut can review, correct or delete them."

| Route | Comportement |
| --- | --- |
| `GET /api/memories/{user_id}` | Consulte uniquement les mémoires de cet utilisateur, par created_at croissant, puis id à date égale. Renvoie 200 et `[]` si l'utilisateur existe sans mémoire, 404 s'il est inconnu. |
| `POST /api/memories` | Ajoute un objet memory complet et renvoie cet objet avec 201. L'utilisateur doit exister ; un id déjà utilisé renvoie 400. |
| `PUT /api/memories/{memory_id}` | Corrige category, content, importance et source, puis renvoie l'objet avec 200. Le corps complet est requis ; id, user_id et created_at doivent rester identiques, sinon 400. |
| `DELETE /api/memories/{memory_id}` | Supprime réellement la ligne SQLite et renvoie 200 avec `{"success": true}`. Une mémoire inconnue renvoie 404, comme pour PUT. |

L'oubli est persistant : la mémoire supprimée disparaît des GET suivants et n'est pas réimportée au redémarrage sur cette base existante. Elle ne doit plus servir à personnaliser les échanges futurs. Les fichiers seeds restent inchangés ; une nouvelle base vide charge à nouveau le dataset de démonstration.

Les sept champs du contrat sont obligatoires. Les chaînes ne peuvent pas être vides ou composées seulement d'espaces ; importance est un entier de 1 à 10 ; created_at est une date ISO 8601 UTC avec suffixe Z (secondes et, éventuellement, 1 à 6 décimales). Les champs supplémentaires sont refusés avec 400. category et source restent des chaînes libres sans enum rigide.

Le router `app/routes/memories.py`, enregistré dans `app/main.py`, utilise les connexions et validations existantes et des requêtes SQL paramétrées. Les requêtes lisent SQLite ; les seeds servent uniquement à initialiser une base vide. Les tests de `tests/test_memories.py` utilisent des bases temporaires et couvrent la validation, les corrections, l'oubli après redémarrage, le tri et la séparation des utilisateurs. Cette séparation filtre les données par utilisateur ; aucune authentification n'est ajoutée.

### Essai dans Swagger

Ouvrir `/docs`, consulter `GET /api/memories/ASTRO-001`, puis envoyer ce corps à `POST /api/memories` :

```json
{
  "id": "MEM-DEMO-001",
  "user_id": "ASTRO-001",
  "category": "coping_strategy",
  "content": "Listening to music helps Alex decompress after stressful situations.",
  "importance": 4,
  "source": "user",
  "created_at": "2080-04-16T18:00:00Z"
}
```

Pour corriger cette mémoire, envoyer le même objet complet à `PUT /api/memories/MEM-DEMO-001`, en remplaçant content par `Alex prefers quiet instrumental music.` et importance par `7`. Supprimer ensuite avec `DELETE /api/memories/MEM-DEMO-001`, puis refaire GET pour vérifier son absence.

### Utilisation par Ollama

L'architecture envisagée est :

```text
Profile
+ Baseline
+ Current Drift
+ Authorized Memories
+ Current Message
        ↓
Ollama
        ↓
Personalized PsychoSpace Response
```

Le compagnon Ollama utilise ce stockage contrôlé par l'utilisateur pour personnaliser ses réponses. Aucune extraction de souvenirs depuis les conversations, mémorisation automatique, surveillance cachée ou nouveau mécanisme de machine learning n'est ajouté.
