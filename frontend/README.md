# PsychoSpace · Foundation UI

Phases 1 et 2 : shell de navigation, présence abstraite, vue d'ensemble et État du jour.
L’interface et les libellés d’accessibilité sont en français, avec dates et nombres
au format français. Les noms techniques et les routes restent inchangés. Le niveau
moderate est formulé « Ton rythme évolue depuis quelques jours. » ; le bouton
« Pourquoi ? » affiche l’explication réelle et le score sous la forme « 62 % ».
Le dossier initial contenait seulement `.gitkeep` ; aucun framework ni style existant.
React 19 + Vite 7, CSS natif, icônes SVG locales et polices système : aucun asset
externe ni CDN à l'exécution. Companion, Evolution, Memory et Care sont des
pages d'attente, sans fonctionnalités métier.

## Lancement local

Depuis la racine du dépôt, lancer le backend existant :

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Puis dans un autre terminal :

```powershell
cd frontend
npm ci
npm run dev
```

Ouvrir http://127.0.0.1:5173. Node 20.19+ ou 22.12+ requis par Vite ; validation
effectuée avec Node 24. La configuration optionnelle `frontend/.env.local` :

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_MISSION_CLOCK_MODE=demo
VITE_MISSION_DEMO_DATE=2080-04-16
```

Le [proxy Vite](https://vite.dev/config/server-options#server-proxy) centralise cette
destination et relaie `/api` sans changer le backend ni sa politique CORS. Le même
proxy est configuré pour `npm run preview` (port 4173). Un hébergement statique du
build doit fournir son propre reverse proxy `/api` vers FastAPI : cette option
Vite n'est pas un serveur de production. Ne placer aucun secret dans `VITE_*`.

L'horloge centralisée `src/utils/missionClock.js` utilise par défaut la date de
mission du 16 avril 2080. À chaque soumission, elle reprend les heures, minutes,
secondes et millisecondes locales de la machine et les place sur cette date de
mission, sérialisée en ISO UTC (`Z`). C'est une horloge de scénario : on ne convertit
pas un instant terrestre de 2026 en 2080 par décalage de fuseau. La date reste fixe,
même au passage de minuit ; les heures continuent de suivre la machine.
`VITE_MISSION_CLOCK_MODE=real` rétablit l'instant UTC réel, sans modifier les
composants. Redémarrer Vite ou reconstruire après changement de configuration.
Une date ou un mode invalide provoque un échec de soumission, sans retour silencieux
à l'année réelle. Les valeurs par défaut sont centralisées dans `src/config.js`.

## Données et comportement

`DEMO_USER_ID` est centralisé dans `src/config.js`. La vue d'ensemble appelle
les quatre GET profile, baseline, drift et checkins. L'État du jour ajoute le POST
checkins ; aucune génération Ollama ni écriture directe SQLite. L'accueil utilise le prénom reçu et l'heure locale du navigateur.
Le dernier drift est sélectionné par detected_at UTC, microsecondes comprises,
puis id ; aucune détection ou modification des scores côté UI. Un score 0.62 est
affiché 62 % uniquement dans le panneau ouvert par « Pourquoi ? », avec un libellé
explicite : ce n'est ni un risque médical ni un diagnostic.

Sleep, Energy, Fatigue et Activity comparent le **dernier check-in** à la baseline,
sans moyenne récente implicite. Les barres sont décoratives, normalisées par
indicateur, et leurs valeurs sont aussi textuelles. La date de la dernière saisie
et la mention des données de démonstration rendent visibles les dates fictives de
2080 : elles ne sont pas présentées comme la journée réelle de l'utilisateur.
Une absence de drift ne signifie pas que le moteur a confirmé une stabilité.
Baseline absente : tirets et indication explicite. Profil absent : vue vide.

`PsychoSpacePresence` accepte idle, thinking, attentive et drift ; idle et drift
servent à la vue d'ensemble, attentive accompagne la saisie. L'événement résolu laisse la présence idle. Les variations
du halo sont discrètes, sans alarme ni code rouge. Les animations sont désactivées
avec `prefers-reduced-motion`. Liens de navigation nommés, focus clavier visibles,
lien d'évitement, bouton d'explication avec `aria-expanded`, états loading/error/empty.
Une panne réseau ou un délai de 12 secondes affiche un message humain et un bouton
de nouvelle tentative ; aucune erreur technique brute ni donnée de remplacement.

## État du jour — phase 2

La page `/#pulse` pose une question à la fois : sommeil, humeur, pression ressentie,
fatigue, énergie, échanges et activité. Aucune réponse n'est présélectionnée.
Les repères proposés sont des choix de saisie, jamais des réponses fictives.
Les cinq scores sont des groupes de boutons radio natifs stylisés, accessibles
par Tab, flèches et Espace. La progression est discrète et le focus suit la question.
Le retour à l'étape précédente conserve les réponses, y compris après une erreur.

Le sommeil est saisi par demi-heures entre 0 et 24 h : `6 h 30` donne `6.5` dans
le JSON. L'activité accepte un repère ou un nombre précis de minutes entières entre
0 et 1 440. Ce sont des bornes de saisie journalière, pas des seuils de santé.
Le dernier bouton envoie uniquement les sept réponses, `DEMO_USER_ID` et un timestamp
UTC fourni au moment de la soumission par `missionTimestamp()`.

Un verrou en mémoire et la désactivation du formulaire empêchent les doubles
clics pendant le POST. Aucune relance automatique. Un refus ou une panne conserve
les réponses et propose « Réessayer ». Le délai réseau est de 30 secondes.
Le contrat n'offre pas d'idempotence : une réponse réseau perdue après enregistrement
peut laisser un résultat incertain ; une nouvelle tentative manuelle peut alors
créer un autre bilan. Les réponses ne sont pas conservées après rechargement ou
sortie de la page, aucun stockage local de données personnelles n'est ajouté.

Après un vrai 201 valide, la confirmation utilise le prénom du profil s'il est
disponible, résume sommeil/énergie/fatigue/activité et propose le retour à la vue
d'ensemble. Aucun drift n'est calculé ou inventé. En mode demo, les nouveaux bilans
du 16 avril 2080 sont postérieurs aux seeds du 15 avril : le tri existant de la vue
d'ensemble les retient comme récents. Les anciens bilans de 2026 sont conservés,
ainsi que les tests de l'horloge réelle ; aucune migration ni suppression.

## Vérification

```powershell
npm run build
npm test
# Avec le frontend et le backend démarrés ; Microsoft Edge installé :
npx playwright test
```

Les tests navigateur utilisent le vrai backend pour Alex, les valeurs du drift,
les quatre métriques et la navigation. Les scénarios panne/vide/chargement et le test de relance
interceptent les réponses réseau. Tests desktop, tablette 768 px, mobile 390 px,
clavier, réduction des animations et absence de requêtes externes. Captures dans
`test-results/` (ignoré par Git). Sur un poste sans Edge, adapter `channel` dans
`playwright.config.js` au navigateur Playwright installé.

Le test d'écriture réelle est désactivé par défaut pour ne pas remplir la base
à chaque exécution. Pour autoriser explicitement une démonstration depuis le navigateur :

```powershell
$env:PSYCHOSPACE_REAL_WRITE = '1'
npx playwright test tests/browser/checkin.spec.js
Remove-Item Env:PSYCHOSPACE_REAL_WRITE
```

Ce test remplit l'interface, effectue un vrai POST et vérifie que le GET contient
exactement les réponses et le timestamp envoyés. Les autres tests couvrent les
bornes, le retour arrière, le clavier, le refus serveur, la relance, le blocage de
double soumission et le responsive, sans écriture réelle.
