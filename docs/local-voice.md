# Voix locale du Compagnon

Le bouton Parler utilise la reconnaissance navigateur uniquement si son mode local
fr-FR est disponible. Sinon, MediaRecorder enregistre au maximum 30 secondes,
puis POST `/api/voice/transcribe` transmet le Blob au FastAPI de cette machine.
FFmpeg produit un WAV PCM signé 16 bits, mono, 16 kHz ; whisper.cpp transcrit
en français, sans traduction. Le texte est ajouté au brouillon : seul le bouton
Envoyer (ou Entrée après transcription) déclenche le chat. Le texte reste modifiable.

## Configuration et lancement

Les variables suivantes sont lues depuis l'environnement, puis `.env.local`
à la racine si elles ne sont pas déjà définies :

| Variable | Valeur |
| --- | --- |
| WHISPER_CLI_PATH | Chemin absolu vers whisper-cli local |
| WHISPER_MODEL_PATH | Chemin absolu vers le modèle déjà téléchargé |
| FFMPEG_PATH | Chemin absolu vers FFmpeg local |
| WHISPER_LANGUAGE | `fr` par défaut |
| WHISPER_TIMEOUT_SECONDS | `30`, budget total conversion + transcription |
| WHISPER_MAX_AUDIO_BYTES | `10485760` (10 Mio) |

`.env.local` est ignoré par Git ; `.env.example` contient des chemins génériques.
Redémarrer FastAPI après une modification de configuration.

Depuis la racine :

```powershell
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Depuis `frontend` : `npm run dev`, puis ouvrir
`http://127.0.0.1:5173/#companion`. Le proxy vocal Vite est fixé à
`http://127.0.0.1:8000`, indépendamment de la configuration des autres routes.
En déploiement avec un autre serveur HTTP, son proxy `/api/voice` doit également
pointer vers le backend de cette machine. L'accès vocal par une adresse LAN est refusé.
Les redirections HTTP sont refusées par le client vocal.

## API et confidentialité

### Nombre de threads Whisper

`WHISPER_THREADS` accepte un entier strictement positif. Non défini ou vide,
le choix prudent est `min(4, max(1, (os.cpu_count() or 1) // 2))` : la moitié
des CPU logiques, plafonnée à quatre. Cela réserve au moins un CPU logique sur
les machines qui en possèdent plusieurs. Sur une machine à un seul CPU (ou si
le nombre est inconnu), un thread est le minimum possible. Il s'agit d'un budget
de threads, pas d'une réservation matérielle ni d'une affinité CPU.

Une valeur explicite remplace ce défaut ; une valeur invalide provoque une erreur
503 contrôlée. Le service ajoute uniquement `-t <nombre>` à whisper-cli. Le modèle,
la langue et les paramètres de décodage ne changent pas. Le log `[VOICE PERF]`
ajoute `whisper_threads=<nombre>` ; avant tout lancement Whisper, il indique
`whisper_threads=non_lancé`. La réponse JSON de performance reste inchangée.

Le diagnostic `backend/scripts/benchmark_whisper.py` est indépendant du runtime :

```powershell
# Racine du projet ; pas besoin de lancer FastAPI, React ou Ollama
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m backend.scripts.benchmark_whisper --synthetic
# Ou, pour un WAV de test existant en PCM 16 bits mono 16 kHz :
.\.venv\Scripts\python.exe -m backend.scripts.benchmark_whisper --wav 'C:\tests\phrase.wav'
```

Le WAV fourni est seulement lu et reste sous le contrôle de son propriétaire ;
le script n'en conserve aucune copie. Le mode synthétique utilise Hortense et
FFmpeg locaux et supprime son audio en sortie. Tous les textes de sortie temporaires
sont également supprimés. Le benchmark utilise obligatoirement `ggml-base.bin`
et `fr`, exécute trois processus par configuration 2/4/6/8 admissible selon
`os.cpu_count()`, et alterne l'ordre entre répétitions. Il mesure uniquement le
processus Whisper avec `perf_counter()`, sans inclure synthèse, conversion ou
lecture du résultat. Il n'applique jamais le gagnant et ne contacte pas Ollama.

Mesure sur cette machine (4 CPU logiques), WAV synthétique français de 5,699 s :

| Threads | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Moyenne (ms) |
| --- | ---: | ---: | ---: | ---: |
| 2 | 6229,418 | 5424,428 | 5445,973 | 5699,940 |
| 4 | 4477,056 | 4489,179 | 4825,459 | 4597,231 |
| 6 | Non exécuté : CPU insuffisants | — | — | — |
| 8 | Non exécuté : CPU insuffisants | — | — | — |

Transcription identique sur les six runs : « Sava, je suis juste fatigué aujourd'hui
et je pense que demain, ça ira mieux. » Le gagnant mesuré est **4 threads**,
avec une moyenne inférieure de **19,35 %** à celle de 2 threads. Le choix automatique
reste prudent (2 ici) ; `.env.local` n'a pas été modifié. Pour privilégier cette
latence après examen des mesures, définir explicitement `WHISPER_THREADS=4` et
redémarrer FastAPI.

Limites : trois runs, un seul court audio synthétique et caches non purgés ; le
premier run inclut les effets possibles du chargement à froid. Ces résultats
ne démontrent pas un gain identique sur tous les enregistrements ou sous charge,
ni une équivalence universelle des transcriptions.

Validation après ajout des threads et du benchmark : **121 tests backend réussis**
(`python -m unittest discover -s backend/tests`), dont les tests de profilage
existants et sept nouveaux tests ciblés. Aucun dossier temporaire de benchmark
ne subsiste après la mesure.

### Détail des mesures

Chaque appel à `/api/voice/transcribe` produit un log INFO `[VOICE PERF]`, y compris
en cas d'erreur. Les mesures utilisent `time.perf_counter()` et sont exprimées
en millisecondes, arrondies à trois décimales. Aucun audio, texte reconnu, chemin
ou argument de commande n'est inclus dans ce log.

| Mesure | Périmètre |
| --- | --- |
| `upload_ms` | Lecture du corps HTTP par FastAPI, jusqu'au dernier fragment |
| `write_ms` | Écriture et fermeture du fichier audio d'entrée |
| `ffmpeg_ms` | Lancement, exécution et attente du processus FFmpeg |
| `whisper_ms` | Lancement, chargement du modèle, transcription et attente du processus Whisper |
| `parse_ms` | Lecture UTF-8 du fichier texte, suppression du BOM et espaces périphériques |
| `cleanup_ms` | Sortie du contexte TemporaryDirectory, incluant la suppression des fichiers |
| `total_ms` | Entrée dans l'endpoint jusqu'à la fin du traitement et du nettoyage |

`upload_ms` ne mesure pas l'enregistrement micro ni le temps passé dans le proxy
avant l'entrée dans FastAPI. `total_ms` comprend les validations, la création du
répertoire et l'attente du thread de traitement ; il peut donc dépasser la somme
des étapes. Il exclut la sérialisation et le transfert de la réponse HTTP, ainsi
que l'émission du log. Sur erreur, les étapes non atteintes valent zéro ; une durée
de nettoyage ne prouve pas à elle seule que ce nettoyage a réussi.

Par défaut, la réponse reste exactement `{text, language, processing_ms}`.
Pour le développement/debug uniquement, définir `WHISPER_PERF_DEBUG=true` dans
l'environnement du backend ou dans `.env.local`, puis redémarrer FastAPI.
La réponse de succès ajoute alors `performance` avec les sept mesures. Les
réponses d'erreur restent inchangées. `processing_ms` conserve son périmètre
historique : traitement du service, sans upload ni attente de son thread.

Test microphone réel, depuis la racine, dans trois terminaux PowerShell
(arrêter d'abord tout ancien serveur occupant les mêmes ports) :

```powershell
# Terminal 1 : backend, configuration locale existante conservée
$env:WHISPER_PERF_DEBUG = 'true'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --log-level info
```

```powershell
# Terminal 2 : frontend existant
npm --prefix frontend run dev
```

```powershell
# Terminal 3 : diagnostic microphone existant, ouvrant Edge
node frontend/tests/real-microphone.mjs
```

Cliquer Parler, attendre « Je t'écoute... », parler puis arrêter. Le terminal 1
affiche les mesures et le terminal 3 la réponse JSON réelle. Il n'est pas
nécessaire de cliquer Envoyer : le profilage s'arrête à la transcription.

Exemple illustratif, pas une mesure réelle :

```text
INFO:     [VOICE PERF] upload_ms=120.000 write_ms=8.000 ffmpeg_ms=640.000 whisper_ms=4200.000 parse_ms=3.000 cleanup_ms=4.000 total_ms=4975.000 whisper_threads=2
```

### Format et conservation

Corps binaire ; MIME acceptés : `audio/webm`, `audio/ogg`, `audio/wav`,
`audio/mpeg`, `audio/mp4`. Les paramètres comme `;codecs=opus` sont acceptés.
Réponse : `{ "text": "…", "language": "fr", "processing_ms": 4261 }`.
`processing_ms` mesure le service complet, conversion et nettoyage compris,
et non uniquement l'inférence Whisper.

Audio vide ou indécodable/MIME non accepté : 400 ; taille excessive : 413 ;
configuration ou outils absents : 503 ; dépassement du délai total : 504.
Une transcription vide renvoie `text: ""` et le navigateur invite à recommencer.
Les erreurs publiques ne contiennent ni commande, ni chemins, ni diagnostics natifs.

Un `TemporaryDirectory` contient l'entrée, le WAV et la sortie texte. Les handles
sont fermés avant l'exécution des outils Windows et le dossier est supprimé après
succès, erreur ou timeout. Aucun audio n'est écrit dans SQLite, le Memory Vault,
les journaux applicatifs ou Ollama. Le service vocal n'appelle aucune API réseau.
FFmpeg n'autorise que les protocoles `file,pipe`. Les processus sont lancés avec
une liste d'arguments et `shell=False`.

Quitter Compagnon arrête l'enregistrement, toutes les pistes et la requête en cours.
Si la requête a déjà atteint le backend, le traitement peut continuer jusqu'à sa
fin ou son timeout ; son répertoire est ensuite supprimé. La synthèse vocale
est arrêtée avant l'ouverture du microphone. Le clavier reste utilisable en cas
d'échec de la reconnaissance.

Limite : une terminaison brutale du processus ou de Windows peut empêcher le
nettoyage Python ; il ne s'agit pas d'un effacement sécurisé du support physique.

## Vérification

```powershell
.venv/Scripts/python.exe -m unittest discover -s backend/tests
.venv/Scripts/python.exe -m unittest discover -s ai/tests
```

Depuis `frontend`, avec FastAPI et Vite lancés :

```powershell
npm test
npx playwright test
npm run build
node tests/real-microphone.mjs
```

Le dernier script ouvre Edge avec le vrai microphone, sans simulation audio.
Cliquer Parler, autoriser le micro, attendre « Je t’écoute... », parler, arrêter,
relire/corriger puis cliquer Envoyer. Le terminal affiche les réponses réelles,
les durées HTTP et les événements natifs de la voix sélectionnée. Il n'écrit
aucun fichier audio. Le chat conserve normalement les messages validés.

## Fonctionnement sans Internet

Le frontend utilise des ressources locales, sans police/CDN externe identifié.
Whisper et FFmpeg ne nécessitent pas Internet une fois installés, de même
qu'Ollama avec son modèle téléchargé et une voix Windows locale déjà installée.
Le téléchargement initial des outils/modèles, l'installation des dépendances et
l'installation facultative du pack de reconnaissance navigateur peuvent utiliser
Internet. Aucune installation de pack n'est déclenchée automatiquement.

Les tests vérifient les requêtes navigateur vers la boucle locale et interdisent
les appels réseau Python dans le service vocal simulé. Cela ne remplace pas un
test avec les interfaces réseau physiques désactivées. Pour ce test manuel,
garder les serveurs locaux ouverts, déconnecter Internet, puis répéter le parcours
microphone → validation → réponse Ollama → lecture locale.

## Fichiers de cette intégration

Créés :

- `backend/app/routes/voice.py`
- `backend/app/services/whisper_service.py`
- `backend/tests/test_voice.py`
- `frontend/src/services/audioRecorder.js`
- `frontend/tests/audioRecorder.test.js`
- `frontend/tests/browser/whisper.spec.js`
- `frontend/tests/real-microphone.mjs`
- `docs/local-voice.md`

Modifiés (y compris l'implémentation partielle présente au début de la reprise) :

- `.env.example`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/tests/test_profile.py`
- `frontend/src/api.js`
- `frontend/src/components/Companion.jsx`
- `frontend/src/components/Companion.css`
- `frontend/src/components/PsychoSpacePresence.jsx`
- `frontend/src/services/speechRecognition.js`
- `frontend/tests/browser/recognition.spec.js`
- `frontend/tests/browser/voice.spec.js`
- `frontend/vite.config.js`

Les chemins réels étaient déjà configurés dans `.env.local`, non versionné.
Le délai local `OLLAMA_TIMEOUT_SECONDS` y a été porté à 300 secondes après
un échec réel : le chargement à froid du modèle dépassait le délai de 60 secondes.
Les répertoires `ai/core/`, `database/schema.sql`, `database/seeds/`, `contracts/`
et `iot/`, ainsi que les moteurs Drift, Memory Vault et Intervention, restent
inchangés.

## Résultats de validation du 24 septembre 2026

- Backend : 109 tests réussis.
- IA : les 23 tests existants réussis.
- Frontend unitaire : 41 tests réussis.
- Edge/Playwright : 41 tests réussis, 6 scénarios réels optionnels ignorés.
- Build Vite réussi ; `git diff --check` sans erreur.
- Microphone réel → MediaRecorder → POST `/api/voice/transcribe` : HTTP 200.
- Texte exact du premier essai : « Sava, je suis fatiguée aujourd'hui. »
- Traitement FFmpeg + Whisper + nettoyage : 17 270 ms ; HTTP : 17 382 ms.
- Aucun dossier `psychospace-voice-*` restant après l'essai.
- Premier envoi Ollama : HTTP 503 après 65 562 ms ; journal Ollama confirmant
  l'interruption du chargement du modèle par le timeout client à 60 secondes.
- Après réglage local du délai à 300 secondes : envoi du texte reconnu depuis
  l'interface, HTTP 200 en 193 210 ms, message et réponse vérifiés dans l'historique.
- Un test réel supplémentaire réussi (en plus des 41 tests navigateur de la suite).
- Voix native : `Microsoft Hortense - French (France)`, `fr-FR`,
  `localService: true`, événements `start` puis `end` observés.
- Test avec connexion Internet physiquement coupée non effectué.

Réponse Ollama exacte :

> La fatigue est à 8 sur 10, comme ces derniers jours.
> Tu as dit que la musique t’aide à te détendre.
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

Ces durées proviennent du test réel sur cette machine, pas d'un benchmark isolé.
La première transcription contient des erreurs (« Sava », « fatiguée »), ce qui
confirme l'intérêt de la relecture avant envoi. Le temps Ollama inclut le chargement
à froid et le traitement du contexte ; il ne mesure pas uniquement la génération.
