# Profilage local du chat

Le modèle, les options de génération, le prompt, le contexte, les limites de
mémoire/historique et le mode non streamé restent inchangés. Le frontend ne change
pas. `WHISPER_THREADS=4` est conservé dans la configuration locale.

## Activation

`CHAT_PERF_DEBUG=false` par défaut : la réponse POST conserve exactement
`user_id`, `role`, `content`, `timestamp`. Avec `CHAT_PERF_DEBUG=true` (environnement
ou `.env.local`, puis redémarrage), elle ajoute `performance`. Le GET historique
et les réponses d'erreur ne changent pas. Les métriques ne sont pas sauvegardées
dans les messages SQLite.

Un log INFO `[CHAT PERF]` est émis pour chaque POST, succès ou erreur. Il ne
contient que des noms de mesures et des valeurs numériques ou `null` : aucun
identifiant utilisateur, message, mémoire privée, prompt, réponse ou chemin.

## Périmètre des mesures

Toutes les mesures locales utilisent `time.perf_counter()` ; durées en ms,
arrondies à trois décimales :

| Mesure | Périmètre |
| --- | --- |
| `context_ms` | Ouverture SQLite, lecture du contexte, fermeture, construction du contexte structuré |
| `prompt_ms` | Construction des messages finaux transmis à Ollama |
| `ollama_ms` | Fonction client complète : vérification locale `/api/show`, appel `/api/chat`, lecture/validation de la réponse et collecte des métriques |
| `persist_ms` | Nouvelle connexion SQLite, transaction atomique des deux messages, commit et fermeture |
| `total_ms` | Entrée dans la route FastAPI, lecture/validation du corps, attente du thread, étapes précédentes et sérialisation normale de la réponse |
| `prompt_chars` | Somme des longueurs des contenus des messages ; hors JSON, noms de rôles et template interne du modèle |

`total_ms` exclut les couches serveur/proxy précédant la route, le log lui-même,
l'ajout du diagnostic JSON et le transfert réseau de la réponse. En cas d'erreur,
il s'arrête lorsque l'exception sort de la route, avant sa conversion globale
en réponse d'erreur. Les étapes non atteintes valent zéro, les données inconnues
valent `null`. Les mesures sont isolées par requête via `ContextVar` et remises
à zéro même en cas d'exception.

`first_token_ms` et `generation_ms` (après le premier token) restent **null** :
avec `stream: false`, le client reçoit une réponse complète sans événement
permettant d'observer le premier token. Aucune estimation n'est présentée comme
une mesure et aucun streaming n'est ajouté.

Les champs numériques Ollama disponibles sont conservés : `load_duration`,
`prompt_eval_count`, `prompt_eval_duration`, `eval_count`, `eval_duration`,
`total_duration`. Les durées brutes sont en **nanosecondes**, conformément à la
[documentation officielle Ollama](https://docs.ollama.com/api/chat).

Conversions et dérivés :

- `ollama_load_ms`, `ollama_prompt_eval_ms`, `ollama_eval_ms`, `ollama_total_ms` : durée brute / 1 000 000.
- `prompt_tokens` = `prompt_eval_count` ; `generated_tokens` = `eval_count`.
- `tokens_per_second` = `eval_count` × 1 000 000 000 / `eval_duration`.
- Pas de division lorsque la durée est nulle ; métrique absente/invalide ignorée sans faire échouer une réponse valable.

`ollama_eval_ms` est le temps interne de génération rapporté par Ollama : il ne
mesure pas spécifiquement la période **après** le premier token. Les durées
Ollama sont des sous-parties de `ollama_ms`, pas des étapes à ajouter au total.

## Benchmark reproductible hors runtime

Depuis la racine, avec Ollama local disponible et son modèle déjà installé :

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m backend.scripts.benchmark_chat
```

Il n'est pas nécessaire de lancer FastAPI ou React : le script appelle la vraie
route POST via le transport ASGI de TestClient et le vrai Ollama local via HTTP.
`http_ms` mesure en plus la durée complète observée par ce client de test ; il
ne représente pas un aller-retour réseau navigateur → FastAPI.

Le script vérifie `/api/ps` sans charger ni décharger de modèle, puis effectue
trois appels séquentiels avec `ASTRO-001` et le message demandé. Il n'effectue
aucun préchargement. Run 1 est potentiellement froid (l'état préalable est affiché),
runs 2 et 3 sont attendus chauds, sans modification de `keep_alive`.

Une sauvegarde SQLite cohérente de la base existante est créée en mode lecture
seule, puis copiée avant chaque run. Le contexte est donc identique, y compris
l'historique existant. Les messages générés sont réellement enregistrés dans
chaque copie, avec la transaction normale ; ils ne contaminent pas le run suivant
ni la base principale. Aucun seed n'est rechargé. Toutes les copies privées
temporaires sont supprimées en fin de benchmark, même sur erreur Python.

Seules les métriques sont affichées. La requête envoyée et les réponses ne sont
jamais imprimées. Aucune modification de modèle, température, `num_predict`,
prompt ou nombre de mémoires n'est effectuée. Des réponses de longueurs différentes
restent possibles, puisque les paramètres de génération existants sont conservés.

## Vérification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests
```

Les tests ciblés couvrent les unités, les métriques absentes/invalides, les logs
privés, le contrat normal et debug, les erreurs, la validation, l'isolation des
mesures, l'absence de streaming, et l'identité des prompts des trois runs sans
écriture dans la base principale.

## Résultats réels sur cette machine

Modèle : `qwen3:4b-instruct-2507-q4_K_M`, configuration existante conservée.
Avant run 1, `/api/ps` indiquait que ce modèle n'était pas chargé. Aucun
préchargement n'a été effectué. Les trois POST ont réussi.

| Mesure (durées en ms) | Run 1 — froid | Run 2 — chaud | Run 3 — chaud |
| --- | ---: | ---: | ---: |
| context_ms | 4,235 | 3,441 | 2,190 |
| prompt_ms | 0,120 | 0,141 | 0,074 |
| ollama_ms | 181067,893 | 52453,957 | 24695,968 |
| load_duration converti en ms | 79839,655 | 94,430 | 5,213 |
| prompt_eval_duration converti en ms | 79018,329 | 4874,515 | 346,966 |
| eval_duration converti en ms | 18853,854 | 21422,492 | 21708,083 |
| total_duration Ollama converti en ms | 178465,303 | 44848,061 | 22120,608 |
| persist_ms | 2308,163 | 168,245 | 350,682 |
| total_ms FastAPI | 183559,128 | 52725,661 | 25054,166 |
| http_ms TestClient | 183978,845 | 53192,451 | 25168,873 |
| prompt_chars | 3296 | 3296 | 3296 |
| prompt_tokens | 1014 | 1014 | 1014 |
| generated_tokens | 54 | 54 | 54 |
| tokens_per_second | 2,864 | 2,521 | 2,488 |
| first_token_ms / generation_ms | null / null | null / null | null / null |

Les mesures brutes, incluant les durées Ollama en nanosecondes, figurent dans
[chat-benchmark-results.json](chat-benchmark-results.json). Aucun contenu de
conversation n'est enregistré dans ce fichier.

### Goulot d'étranglement observé

L'appel Ollama représente respectivement **98,64 %, 99,48 % et 98,57 %** du total
FastAPI. À froid, chargement du modèle (79,84 s) et évaluation du prompt (79,02 s)
dominent. La construction SQLite du contexte et du prompt reste de quelques
millisecondes ; la persistance atteint néanmoins 2,31 s au premier run.

Le run 3 est 7,33 fois plus rapide que le run 1. À chaud sur ce run, la génération
des 54 tokens domine : **21,71 s**, à **2,488 tokens/s**. Le chargement (5 ms) et
l'évaluation du prompt (347 ms) sont devenus faibles. La génération elle-même
n'a pas accéléré entre froid et chaud : le gain concerne surtout les autres phases.

La variabilité du run 2 ne doit pas être masquée : le total interne Ollama de
44,85 s dépasse la somme chargement + prompt + génération de **18,46 s**.
Cet intervalle n'est pas attribuable précisément avec les métriques disponibles.
L'écart entre `ollama_ms` et le total interne est de **2,60 / 7,61 / 2,58 s** ;
il inclut notamment les opérations client et `/api/show`, non chronométrées
séparément. Il ne peut pas être attribué intégralement au réseau ni au chargement.

Conclusion de mesure : Ollama est le goulot d'étranglement ; à froid les coûts
identifiés sont le chargement et l'évaluation initiale du prompt ; à chaud stable,
la génération. Aucun réglage d'optimisation n'a été appliqué. Trois runs avec
cache progressivement réchauffé ne constituent pas une garantie de latence
sur d'autres messages ou sous une autre charge système.

Validation : **132 tests backend réussis**, dont 11 nouveaux tests ciblés.
`git diff --check` sans erreur. Aucun dossier temporaire de benchmark restant.
