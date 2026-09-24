# Comparaison contrôlée des variantes Ollama

Cette expérience n'est pas importée par le runtime. Aucun changement du frontend,
du schéma SQLite, des moteurs Drift/Memory Vault/Intervention, du client de
production ou de la configuration permanente n'est effectué.

## Protocole

Modèle fixe : `qwen3:4b-instruct-2507-q4_K_M`. Message et utilisateur identiques
pour tous les appels : `ASTRO-001`, « Ça va, je suis juste fatigué aujourd'hui. »

Les variantes sont cumulatives :

| Variante | Système | Contexte | Sortie |
| --- | --- | --- | --- |
| A | Texte de production exact | Contexte de production exact | Options existantes, num_predict=160 sur cette machine |
| B | Système compact | Identique à A | Identique à A |
| C | Identique à B | Profil minimal, dernier drift, au plus 2 check-ins distincts, 2 mémoires pertinentes, 4 messages d'historique | Identique à A |
| D | Identique à C + consignes de concision | Identique à C | num_predict=min(80, valeur existante) |

Le système compact préserve identité, ton calme, absence de diagnostic, choix
utilisateur, ancrage factuel, distinction faits/hypothèses, autonomie du Drift
Engine, absence de mémorisation automatique et de simulation des proches, et
traitement du contexte comme des données. Il demande au plus une action facultative.
D évite en plus introductions, scores non nécessaires et répétition du message.

Le profil minimal contient prénom et préférence de soutien. La baseline est
omise en C/D. Le dernier drift est conservé sans recalcul, avec son horodatage
et un extrait exact de l'explication limité comme dans le prompt actuel.
Les check-ins restent dans l'ordre chronologique ; les doublons exacts sont
retirés. Aucune valeur n'est synthétisée pour remplir les blocs vides.

La pertinence des mémoires est déterministe : correspondances lexicales après
normalisation des accents, puis vocabulaire associé à la fatigue (repos, sommeil,
calme, musique, détente…). Les égalités suivent l'ordre autorisé déjà fourni par
le contexte de production. Les doublons sont retirés, les scores nuls exclus,
et seules les deux premières mémoires sont retenues. Aucun autre utilisateur
n'est consulté. Ce petit classement lexical est expérimental et ne constitue
pas un moteur général de pertinence sémantique.

Une sauvegarde cohérente et temporaire de SQLite est créée en lecture seule.
Chaque appel utilise une nouvelle copie de ce même état : les réponses sont
persistées par la vraie route dans cette copie, jamais dans l'historique principal.
Le prompt d'une variante est donc strictement identique pour ses quatre appels.
Les copies privées sont supprimées en fin d'expérience, même sur exception Python.

Ordre : A, B, C, D. Pour chaque variante, un appel réel d'échauffement non compté,
puis **trois appels chauds consécutifs**. Les moyennes excluent les échauffements.
Cela réchauffe également le cache du prompt de chaque variante ; les mesures
ne représentent pas le coût du premier message avec un contexte nouveau.

Le script utilise la vraie route FastAPI en processus via TestClient et le vrai
client Ollama. Des adaptations limitées au processus du benchmark remplacent
la construction des messages et les options de D. Les requêtes HTTP ne sont
pas simulées. Un `keep_alive=30m` commun aux quatre variantes garde le modèle
chargé entre les runs ; le réglage de production n'est pas modifié. `stream=false`,
la température et `num_ctx` restent identiques pour les quatre variantes.

## Exécution

Depuis la racine, avec Ollama local disponible :

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m backend.scripts.benchmark_ollama_variants --output docs/ollama-variants-results.json
```

Le rapport contient les métriques et les réponses générées, comme demandé pour
la revue qualitative ; il ne contient pas les prompts ou les blocs de mémoires.
Les logs `[CHAT PERF]` du runtime restent limités aux métriques numériques.

`total_ms` est la durée de la route FastAPI instrumentée (contexte, prompt,
client Ollama et persistance inclus). `prompt_eval_ms` et `eval_ms` sont les
durées internes Ollama converties en ms. `done_reason` permet de repérer une
sortie interrompue par la limite de tokens. Le rapport conserve `ollama_load_ms`
pour vérifier que le coût de chargement n'explique pas le classement.

## Tests et limites

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests
```

Les tests couvrent la référence exacte A, la différence isolée B, l'intégrité du
contexte, la sélection déterministe, les limites C/D, l'isolation utilisateur,
les paramètres envoyés au vrai client, et l'exclusion des quatre échauffements
avec préservation de la base principale.

Trois runs et un seul message ne suffisent pas à garantir une amélioration sur
tous les usages. L'ordre fixe peut subir des variations de charge ou thermiques.
Les caches sont réchauffés, sans purge ni changement de seed/température.
La revue humaine porte sur les réponses obtenues, leur concision, leur ancrage,
leur ton, la répétition des scores et l'éventuelle troncature. Aucune variante
n'est appliquée automatiquement à l'issue du benchmark.

## Résultats réels

139 tests backend réussis, dont 7 nouveaux tests ciblés. Les 12 runs mesurés ont réussi, ainsi que les quatre échauffements exclus. Tous les runs mesurés ont terminé avec `done_reason=stop` ; aucun n’a été tronqué. Aucun dossier temporaire ne reste.

### Moyennes

| Variante | Caractères | Tokens prompt | Tokens générés | Prompt eval (ms) | Génération (ms) | Total (ms) | Tokens/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 3361.000 | 1028.000 | 52.667 | 322.215 | 18891.518 | 22260.805 | 2.804 |
| B | 2742.000 | 869.000 | 54.000 | 381.806 | 18135.326 | 29432.600 | 2.980 |
| C | 2027.000 | 648.000 | 40.000 | 269.379 | 10517.537 | 13607.151 | 3.812 |
| D | 2173.000 | 686.000 | 47.000 | 271.706 | 14362.488 | 17511.661 | 3.267 |

### Les douze runs

| Variante/run | Caractères | Tokens prompt | Tokens générés | Prompt eval (ms) | Génération (ms) | Total (ms) | Tokens/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A/1 | 3361 | 1028 | 50 | 333.016 | 16390.159 | 19736.822 | 3.051 |
| A/2 | 3361 | 1028 | 54 | 301.419 | 20313.418 | 23672.33 | 2.658 |
| A/3 | 3361 | 1028 | 54 | 332.21 | 19970.978 | 23373.264 | 2.704 |
| B/1 | 2742 | 869 | 54 | 296.748 | 18616.885 | 21694.942 | 2.901 |
| B/2 | 2742 | 869 | 54 | 343.883 | 17438.685 | 21475.526 | 3.097 |
| B/3 | 2742 | 869 | 54 | 504.788 | 18350.408 | 45127.331 | 2.943 |
| C/1 | 2027 | 648 | 39 | 241.435 | 11237.27 | 14414.901 | 3.471 |
| C/2 | 2027 | 648 | 44 | 252.05 | 10870.065 | 13895.777 | 4.048 |
| C/3 | 2027 | 648 | 37 | 314.652 | 9445.276 | 12510.774 | 3.917 |
| D/1 | 2173 | 686 | 36 | 260.1 | 11435.584 | 14434.98 | 3.148 |
| D/2 | 2173 | 686 | 59 | 281.296 | 18083.13 | 21365.806 | 3.263 |
| D/3 | 2173 | 686 | 46 | 273.721 | 13568.75 | 16734.197 | 3.39 |

### Réponses intégrales

**A — run 1**

> La fatigue est à 8, comme ces derniers jours.  
> Tu as dit que la musique t’aide à te détendre.  
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

**A — run 2**

> La fatigue est à 8 sur 10, comme ces derniers jours.  
> Tu as dit que la musique t’aide à te détendre.  
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

**A — run 3**

> La fatigue est à 8 sur 10, comme ces derniers jours.  
> Tu as dit que la musique t’aide à te détendre.  
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

**B — run 1**

> Comme tu le dis, la fatigue est à 8 sur 10.  
> Tu as dit que la musique t’aide à te détendre.  
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

**B — run 2**

> Comme tu le dis, la fatigue est à 8 sur 10.  
> Tu as dit que la musique t’aide à te détendre.  
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

**B — run 3**

> Comme tu le dis, la fatigue est à 8 sur 10.  
> Tu as dit que la musique t’aide à te détendre.  
> Voudrais-tu écouter une playlist de sons de nuit ou de constellations ?

**C — run 1**

> Comprendu. La fatigue est un signal, pas une maladie.  
> Tu veux que je te propose une courte séance de musique ou une activité physique douce ?

**C — run 2**

> Comprendu. Tu as déjà noté une baisse d’activité et de sommeil ces derniers jours.  
> Voudrais-tu écouter une playlist douce pour te détendre ?

**C — run 3**

> Comprendu. La fatigue est un signal, pas une maladie.  
> Tu veux écouter une mélodie douce ou simplement discuter de ton jour ?

**D — run 1**

> Comprendu. La fatigue est un signal, pas une maladie.  
> Tu veux que je te propose une musique douce ou une activité physique légère ?

**D — run 2**

> Comprendu. Tu as 5,6 heures de sommeil aujourd’hui.  
> Peut-être que du calme, de la musique ou une marche de 15 minutes t’aidera.  
> Tu veux que je t’envoie une playlist ?

**D — run 3**

> Comprendu. Tu as 5,6 heures de sommeil aujourd’hui.  
> Peut-être que 10 minutes de marche douce ou une chanson apaisante t’aideraient.


### Échauffements exclus

- A : total 167094.825 ms, chargement 64749.462 ms.
- B : total 97767.876 ms, chargement 6.117 ms.
- C : total 51910.325 ms, chargement 9.373 ms.
- D : total 51941.636 ms, chargement 11.621 ms.

[Résultats JSON complets](ollama-variants-results.json).

### Analyse de vitesse et de qualité

**C gagne en vitesse sur cet échantillon** : 13,607 s contre 22,261 s pour A,
soit **38,87 % de réduction** du temps moyen. Ses trois runs sont tous plus
rapides que chacun des runs A. D réduit la moyenne de 21,33 % par rapport à A,
mais reste plus lente que C. D génère en moyenne 47 tokens, contre 40 pour C ;
le plafond de 80 tokens n'est atteint sur aucun run. On ne peut donc pas attribuer
un gain au simple abaissement de ce plafond.

B a une moyenne de 29,433 s (+32,22 % par rapport à A), fortement influencée
par son run 3 à 45,127 s. Sa médiane est de 21,695 s, contre 23,373 s pour A.
Le run lent reste inclus dans la moyenne demandée : ses 18,350 s de génération
n'expliquent pas à elles seules le total de 45,127 s. Les champs conservés dans
ce benchmark ne permettent pas de localiser précisément le temps restant.
Trois échantillons ne suffisent pas à conclure que B est systématiquement plus lente.

Les évaluations des prompts réchauffés prennent en moyenne 0,27 à 0,38 s :
réduire le prompt n'apporte pas ici un gain proportionnel au nombre de tokens
d'entrée. C produit moins de tokens et présente également un débit observé plus
élevé. Ces observations ne permettent pas de séparer causalement tous les effets
du contexte, de la formulation, du cache et de la charge système.

Revue qualitative des réponses, limitée à ce message :

- **A** : trois phrases complètes, proposition musicale liée au contexte, mais
  rappel du score de fatigue non demandé et formulation répétitive. Pas de réponse
  tronquée ni excessivement courte.
- **B** : contenu presque identique à A, avec un défaut d'attribution : « Comme
  tu le dis, la fatigue est à 8 sur 10 ». Le message de test ne donne aucun score.
  Le score provient du contexte, pas de cette déclaration de l'utilisateur.
- **C** : réponses plus courtes, mais encore complètes. Les runs 1 et 3 commencent
  par « Comprendu. La fatigue est un signal, pas une maladie. » : formule générique,
  plus mécanique et médicalisée sans demande. Ils proposent deux options au lieu
  d'une seule action. Le run 2 conserve une référence contextuelle au sommeil et
  à l'activité ainsi qu'une proposition musicale. La personnalisation est donc
  variable, pas totalement perdue. La baseline et une partie de l'historique et
  des mémoires ont été omises intentionnellement ; leur utilité sur d'autres
  messages n'est pas évaluée ici.
- **D** : ne corrige pas la formule d'introduction, ni l'accumulation de propositions.
  Les runs 2 et 3 rattachent « 5,6 heures de sommeil » à « aujourd'hui », alors que
  le bloc des check-ins fourni n'est pas daté. Le run 2 propose calme, musique et
  marche, puis un envoi de playlist que le parcours testé ne réalise pas. Les
  instructions de concision sont donc insuffisantes pour garantir le comportement
  humain attendu. Aucun de ces défauts ne vient d'une troncature à 80 tokens.

**Décision : aucune variante adoptée automatiquement.** C est la gagnante de
vitesse mesurée, mais la conservation de la qualité humaine n'est pas démontrée.
Le runtime garde le prompt, le contexte et les paramètres actuels de A.
