# Dataset commun ASTRO-001

Ce dataset officiel de développement représente Alex, astronaute fictif de 34 ans, pour la mission HORIZON-2080-01. Les quatre membres du groupe utilisent les mêmes données pour les tests du frontend, du backend, de l'IA et de l'IoT. Toutes les données sont entièrement fictives ; elles ne décrivent aucune personne réelle et ne constituent aucun diagnostic médical ou psychiatrique.

## Fichiers et formats

| Fichier | Contenu | Contrat de chaque objet |
| --- | --- | --- |
| astro-001-profile.json | Un objet profil | [profile](../../contracts/data/profile.example.json) |
| astro-001-memories.json | Tableau de 6 mémoires | [memory](../../contracts/data/memory.example.json) |
| astro-001-checkins.json | Tableau de 15 bilans | [daily-checkin](../../contracts/data/daily-checkin.example.json) |
| astro-001-sensors.json | Tableau de 90 mesures | [sensor-reading](../../contracts/data/sensor-reading.example.json) |
| astro-001-baseline.json | Un objet baseline | [baseline](../../contracts/data/baseline.example.json) |
| astro-001-drift-events.json | Tableau de 2 événements | [drift-event](../../contracts/data/drift-event.example.json) |
| astro-001-interventions.json | Tableau de 4 propositions | [intervention](../../contracts/data/intervention.example.json) |

Les objets reprennent exactement les champs des contrats, sans métadonnées supplémentaires. Aucune importation SQLite n'est effectuée.

## Chronologie

La période couvre le **1er au 15 avril 2080**, avec un bilan quotidien à 18 h UTC et six mesures de capteurs par jour. Les six mémoires sont datées du matin du jour 1. L'état final des événements et interventions correspond au soir du jour 15, après les propositions.

- **Jours 1 à 7 (1er–7 avril)** : état habituel stable, avec une variabilité quotidienne normale. Ces sept bilans constituent la référence personnelle.
- **Jours 8 à 11 (8–11 avril)** : variation progressive ; le sommeil, l'activité et les interactions diminuent tandis que la fatigue augmente. Un premier événement léger apparaît au jour 10 après plusieurs observations concordantes.
- **Jours 12 à 15 (12–15 avril)** : dérive silencieuse plus visible. Au jour 15, sommeil de 5,6 h, humeur de 5/10, stress de 7/10, fatigue de 8/10, énergie de 4/10, niveau social de 3/10 et activité de 18 min. Le second événement apparaît après le bilan du jour 15.

Une seule mauvaise journée ne représente pas une dérive. La tendance résulte de plusieurs jours et de plusieurs observations ; la variabilité des premiers jours ne produit aucun événement.

## Baseline réellement calculée

La baseline est calculée le 7 avril à 18 h 05 UTC, après le septième bilan, exclusivement à partir des jours 1 à 7 : `observation_days = 7`. Chaque moyenne est la somme des sept valeurs divisée par sept, arrondie à six décimales. Les jours suivants ne contribuent pas à cette référence.

| Champ | Somme sur 7 jours | Moyenne stockée | Unité |
| --- | --- | --- | --- |
| sleep_hours_avg | 51.4 | 7.342857 | heures |
| mood_avg | 52 | 7.428571 | échelle 1 à 10 |
| stress_avg | 21 | 3 | échelle 1 à 10 |
| fatigue_avg | 21 | 3 | échelle 1 à 10 |
| energy_avg | 56 | 8 | échelle 1 à 10 |
| social_level_avg | 56 | 8 | échelle 1 à 10 |
| activity_minutes_avg | 385 | 55 | minutes |

Les 7,3 h du profil représentent une habitude déclarée arrondie, distincte de la moyenne calculée.

## Capteurs complémentaires

Chaque jour comprend deux mesures de fréquence cardiaque au repos (08 h et 17 h 30, en bpm), deux mesures de SpO2 relativement stables (08 h 01 et 17 h 31, en %) et deux mesures de mouvement (12 h et 17 h, en m/s²).

Pour cette simulation, `movement` représente l'amplitude scalaire de l'accélération dynamique, après retrait de la composante de gravité, à des créneaux comparables. Les valeurs diminuent progressivement après la période stable. Elles ne sont ni un nombre de pas, ni une mesure directe des minutes d'activité. Deux échantillons par jour illustrent un signal complémentaire et ne suffisent pas à estimer l'activité de toute la journée.

Ces valeurs sont choisies pour un scénario de développement, sans calibration clinique. Aucun capteur ne justifie à lui seul une conclusion sur la santé ou un diagnostic.

## Préférences et compatibilité

- `preferred_support` reste une chaîne, conformément au contrat : elle décrit musique, activité physique et conversation calme.
- Le souhait « evening » est représenté par `19:00:00Z`, car le contrat exige une heure UTC. Les mémoires rappellent cette préférence pour le soir.
- Le niveau léger est `low`, valeur autorisée par le contrat, plutôt que `mild`. Le second événement utilise `moderate`.
- `interests` et `affected_signals` sont des tableaux JSON ; `accepted` et `completed` sont des booléens JSON.
- Les événements et leurs scores sont des annotations fictives pour tester les échanges, pas les résultats d'un algorithme implémenté ni des seuils à reproduire.

## Soutien personnalisé

Les propositions s'appuient sur les mémoires : musique au jour 10, courte activité physique au jour 11, respect d'un temps seul puis conversation calme au jour 15. La dernière proposition évoque aussi la famille et l'astronomie. Chaque intervention référence un événement déjà détecté pour ASTRO-001.

Les deux premières pauses ont été acceptées et réalisées, sans présumer d'un retour immédiat aux habitudes. Les cinq minutes d'activité proposées au jour 11 peuvent se dérouler après le bilan de 18 h et ne sont donc pas ajoutées à celui-ci. Le temps tranquille du jour 15 est terminé avant la proposition de conversation de 19 h 25 ; cette dernière n'a pas d'acceptation confirmée. `accepted = false` ne distingue pas attente et refus.

Ces fichiers servent de données communes de test uniquement. Ils ne créent ni API, ni base de données, ni fonctionnalité.
