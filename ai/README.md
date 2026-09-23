# PsychoSpace — Drift Engine déterministe

Cette brique compare les observations récentes à la **baseline personnelle** de l'astronaute. Elle ne compare pas Alex à une norme de population et ne définit pas un état humain « normal ». Aucun apprentissage automatique, LLM, appel réseau, API ni accès SQLite n'est utilisé. Tout fonctionne avec la bibliothèque standard Python, sans dépendance à installer.

## Exécuter

Depuis la racine du projet, avec Python 3.10 ou supérieur :

```powershell
python -m unittest discover -s ai/tests -v
python ai/demo.py
```

La démonstration est également disponible avec `python -m ai.demo`. Les chemins des seeds sont résolus depuis le fichier Python, indépendamment du répertoire courant. Les fichiers communs sont uniquement lus.

## Organisation

- `core/data_loader.py` : charge les check-ins et les capteurs depuis les deux vrais fichiers ASTRO-001 ; contrôle champs, types, valeurs finies, identifiants et dates.
- `core/baseline.py` : calcule les moyennes des premiers jours observés.
- `core/drift_engine.py` : calcule les écarts, sévérités, score, persistance, contexte capteurs et explication.
- `tests/` : tests unittest sur le vrai dataset et copies en mémoire pour les cas limites. Les erreurs de lecture utilisent des fichiers temporaires supprimés ensuite.
- `demo.py` : compare la période stable et la fin des 15 jours.

## Baseline et fenêtres

`calculate_baseline(checkins, observation_days=7)` trie les check-ins et utilise les **sept premiers jours observés**, sans aucune moyenne codée en dur. Les moyennes sont arrondies à six décimales. `observation_days` compte les jours effectivement utilisés. La forme retournée reprend exactement les champs du contrat baseline.

`calculated_at` correspond ici au timestamp du dernier bilan de référence pour rendre le calcul reproductible. Le seed de baseline indique 18 h 05, tandis que le bilan du jour 7 est à 18 h : ce sont des instants de calcul/coupure différents, pas une différence de moyennes.

Une liste vide, des champs manquants ou supplémentaires, des valeurs invalides, plusieurs utilisateurs mélangés, ou plusieurs bilans le même jour sont refusés par une erreur explicite. L'agrégation de plusieurs bilans quotidiens reste à définir ; aucune règle n'est inventée silencieusement. Le calcul de baseline exige le nombre demandé de jours. Les jours de référence peuvent avoir des lacunes : ce sont des jours observés, pas nécessairement consécutifs.

`analyze_drift(checkins, baseline, sensor_readings=None, recent_window=3)` utilise les jours calendaires allant de la date du dernier bilan moins deux jours à cette date incluse. Une fenêtre incomplète utilise uniquement les observations présentes et réduit la confiance. `recent_window_days` indique le nombre réellement observé, sans imputation. Les dates sont en ISO 8601 UTC avec `Z`, éventuellement avec des fractions de seconde jusqu'à six décimales. Une baseline postérieure au dernier bilan analysé est refusée.

Dans la démonstration, la baseline couvre les jours 1 à 7, la fenêtre stable les jours 5 à 7 et la fenêtre finale les jours 13 à 15. La comparaison stable réutilise donc une partie des données de référence : elle illustre le fonctionnement, sans constituer une évaluation indépendante.

## Formule explicable

Pour chaque signal, `change = recent_mean - baseline_mean`. Seules les directions indiquées ci-dessous contribuent. Une variation inverse donne une sévérité nulle.

| Signal | Direction prise en compte | Écart donnant une sévérité de 1 | Poids |
| --- | --- | --- | --- |
| sleep_hours | diminution | 25 % de la baseline | 0,15 |
| mood | diminution | 3 points | 0,15 |
| stress | augmentation | 3 points | 0,15 |
| fatigue | augmentation | 3 points | 0,15 |
| energy | diminution | 3 points | 0,10 |
| social_level | diminution | 3 points | 0,15 |
| activity_minutes | diminution | 50 % de la baseline | 0,15 |

Pour une diminution : `severity = clamp((baseline - recent) / scale, 0, 1)`.
Pour une augmentation : `severity = clamp((recent - baseline) / scale, 0, 1)`.
`scale` vaut respectivement `baseline × 0.25`, `baseline × 0.50`, ou `3` selon le tableau. Une durée de référence nulle donne une sévérité nulle pour sa diminution, car les durées négatives sont refusées.

**Drift Score = 100 × somme(severity × weight)**, borné entre 0 et 100, puis arrondi à deux décimales. Les poids totalisent 1. Toutes les sévérités contribuent, même en dessous du seuil d'affichage des signaux affectés. Un seul signal ne peut contribuer que 10 ou 15 points au maximum.

Le niveau est déterminé à partir du score arrondi affiché :

| Score | Niveau interne |
| --- | --- |
| 0 ≤ score < 20 | stable |
| 20 ≤ score < 40 | mild |
| 40 ≤ score < 60 | moderate |
| 60 ≤ score ≤ 100 | high |

Ces seuils sont des règles de prototype demandées pour cette étape, sans validation clinique.

## Signaux, persistance et explication

Un signal apparaît dans `affected_signals` si sa sévérité non arrondie est au moins 0,25. Le détail inclut baseline, moyenne récente, changement signé, sévérité, direction et `persistence_days`. `change_percent` est ajouté pour sommeil et activité, où une comparaison relative est pertinente ; les indicateurs 1–10 restent exprimés en points.

`persistence_days` compte les jours observés dans la direction concernée par rapport à la baseline, même si l'écart quotidien est faible. Ce compteur descriptif ne multiplie pas le score. Les détails sont arrondis à six décimales, après calcul.

L'explication est construite à partir des seuls signaux affectés : nom du signal, sens de variation, référence, moyenne récente et nombre de jours concernés. Elle ne prétend pas à une progression monotone que les seules moyennes ne démontrent pas. S'il n'y a aucun signal affecté, elle indique simplement que le seuil d'affichage n'a été atteint par aucun signal.

## Capteurs et confiance

Les capteurs acceptent le format générique du contrat. Le contexte V0.1 décrit seulement `heart_rate`, `spo2` et `movement` ; les autres types valides sont chargés mais ne contribuent pas à cette analyse. Les unités connues doivent correspondre aux contrats : bpm, %, m/s².

Les mesures postérieures au dernier bilan analysé sont exclues. Le contexte contient les moyennes **des moyennes quotidiennes**, le nombre de jours et le nombre de mesures, pour éviter qu'une journée plus échantillonnée pèse davantage. Les seuls jours récents considérés sont ceux ayant un bilan.

Pour movement, le moteur compare aux mêmes jours de référence que la baseline, si ces jours sont disponibles dans les check-ins fournis et si chaque jour dispose de mesures. Il retourne `confirms_activity_decrease: true` uniquement si l'activité déclarée et le mouvement moyen baissent tous deux. Sans référence suffisante, cette valeur et la moyenne de référence sont `null` ; ce manque n'est pas traité comme une confirmation. Sans capteurs, `sensor_context` vaut `{}`.

**Aucun capteur ne modifie le score**, y compris movement. Les valeurs de fréquence cardiaque et SpO2 restent des observations sans interprétation médicale.

`confidence = (jours récents observés / fenêtre demandée) × min(observation_days / 7, 1)`, arrondie à six décimales. Les champs obligatoires étant tous validés, aucune complétude partielle n'est devinée. Une confiance de 1 signifie seulement que ces critères de couverture sont remplis : elle ne garantit ni la fiabilité d'une déclaration ni une probabilité médicale. La présence des capteurs ne change pas cet indicateur.

## Compatibilité avec les contrats et le dataset

Le résultat est un **contexte interne d'analyse**, pas un objet `drift-event` prêt à être stocké ou envoyé par l'API. Les demandes de cette étape diffèrent du contrat commun :

| Élément | Résultat interne demandé | Contrat drift-event existant |
| --- | --- | --- |
| drift_score | 0 à 100 | 0 à 1 |
| level | stable, mild, moderate, high | low, moderate, high |
| affected_signals | objet de détails par signal | tableau de noms |
| autres champs | recent_window_days, sensor_context | id, detected_at, status |

Une future intégration devra définir un adaptateur validé par l'équipe : conversion du score, politique pour stable, correspondance mild/low, extraction des noms de signaux et création des métadonnées d'événement. Aucun contrat existant n'est modifié et aucun identifiant ou statut d'événement n'est inventé ici.

Les moyennes recalculées concordent avec la baseline du dataset. Les événements fictifs fournis dans les seeds sont des annotations illustratives, pas une sortie attendue de ce nouveau moteur. Le niveau final peut donc être `high` ici alors que l'événement fictif est `moderate`. Il ne faut pas modifier le dataset pour faire correspondre ces deux conventions. Les dates 2080 sont conservées telles quelles ; le calcul ne dépend pas de la date de l'ordinateur.

## Limites et future brique Ollama

PsychoSpace ne pose **aucun diagnostic médical ou psychiatrique**. Le score décrit uniquement certains écarts par rapport aux habitudes personnelles. La fenêtre de trois jours atténue une mauvaise observation isolée, mais ne garantit pas à elle seule l'absence de faux signal si plusieurs indicateurs changent fortement. Les effets du contexte de mission, les changements d'horaires, l'évolution de la baseline et l'incertitude des capteurs ne sont pas modélisés ici. Les deux échantillons de mouvement quotidiens du dataset ne résument pas toute l'activité d'une journée.

Architecture future :

```text
Check-ins + Sensors
        ↓
Personal Baseline
        ↓
Drift Engine
        ↓
Structured Context
        ↓
Ollama
        ↓
Human-centered response
```

Ollama pourra reformuler le contexte structuré en une réponse humaine adaptée, sans recalculer les scores ni inventer des observations. Il n'est ni installé ni appelé dans cette version.
