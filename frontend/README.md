# PsychoSpace · Foundation UI

Phases 1 à 4A : shell de navigation, présence abstraite, vue d'ensemble, État du jour, Compagnon et Mon évolution.
L’interface et les libellés d’accessibilité sont en français, avec dates et nombres
au format français. Les noms techniques et les routes restent inchangés. Le niveau
moderate est formulé « Ton rythme évolue depuis quelques jours. » ; le bouton
« Pourquoi ? » affiche l’explication réelle et le score sous la forme « 62 % ».
Le dossier initial contenait seulement `.gitkeep` ; aucun framework ni style existant.
React 19 + Vite 7, CSS natif, icônes SVG locales et polices système : aucun asset
externe ni CDN à l'exécution. Memory et Care sont des
pages d'attente, sans fonctionnalités métier.

## Mon évolution — Phase 4A

`/#evolution` lit exclusivement les GET checkins, baseline et drift d'ASTRO-001.
Une trace SVG commune représente sommeil, énergie, fatigue et activité avec
quatre motifs de trait. La référence douce correspond au rythme habituel.
Le ratio `(valeur - référence) / référence` sert uniquement au dessin ; la
sélection d'un jour affiche les valeurs originales et leurs unités.

Les bilans sont triés chronologiquement, puis le dernier de chaque jour est
présenté (précision des microsecondes conservée). Une période mensuelle évite
d'écraser avril 2080 avec les anciens bilans de 2026, qui restent accessibles.
L'axe respecte les timestamps et les journées absentes interrompent les traits.
Une référence absente ou nulle masque seulement la comparaison concernée.
Le repère utilise le `detected_at` du dernier drift réel ; son explication et
ses signaux viennent de l'API. Aucun Drift Engine ni appel Ollama côté page.
Le résumé décrit uniquement les comparaisons partagées par les trois derniers
jours renseignés de la période, sans calculer de nouvelle détection.

La sélection fonctionne au clic, au toucher et au clavier. Les libellés et
valeurs complètent les couleurs ; la trace défile horizontalement sur tablette.
Les tests navigateur vérifient les trois GET réels, les valeurs et la référence,
le drift, les états vide/erreur/chargement et l'affichage étroit.

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
checkins ; le Compagnon utilise GET et POST chat pour converser avec Ollama via
FastAPI. Aucune écriture directe SQLite. L'accueil utilise le prénom reçu et l'heure locale du navigateur.
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

## Compagnon — phase 3

La page `/#companion` lit l'historique réel via `GET /api/chat/ASTRO-001` et présente
un transcript chronologique, avec prénom issu du profil et signature PsychoSpace.
Pas de bulles standard, de messages préremplis ni de réponse fabriquée côté UI.
L'accueil vide est un texte d'interface, pas un message persisté. Les textes de
conversation sont rendus comme du texte, sans HTML ni Markdown exécutable.

Le textarea est labellisé ; Entrée envoie, Maj + Entrée insère une ligne, et une
composition de texte en cours n'envoie pas. Un message vide est refusé. Le verrou
d'envoi et les contrôles désactivés bloquent une seconde soumission simultanée.
Le POST contient uniquement user_id et message, conformément au contrat. Les dates
du chat restent celles du serveur, sans réécriture frontend ni date affichée :
l'horloge de mission concerne les check-ins seulement.

La présence passe attentive → thinking → attentive. Après 20 secondes, le texte
d'attente change discrètement, sans pourcentage. Aucun timeout frontend n'est fixé
pour le POST ; le backend maîtrise le délai de génération. Les GET d'historique ont
un délai de 15 secondes. Pour un chargement à froid lent sur ce poste, le serveur
existant peut être lancé avec `OLLAMA_TIMEOUT_SECONDS=300` dans son environnement,
sans changer son code ni le modèle. Un backend réglé à 60 s peut toujours renvoyer
une indisponibilité au chargement initial ; le frontend ne masque pas cet échec.

Le brouillon reste dans le textarea pendant l'attente et après échec. Il n'est pas
ajouté à l'historique avant confirmation. Après succès, la réponse réelle du POST
est affichée, puis remplacée par l'historique GET contenant les identifiants serveur.
Si ce GET échoue, le reçu réel reste visible et seule une actualisation est proposée,
sans refaire le POST. Avant une reprise après échec, l'historique est relu : si le
même nouvel échange y figure déjà, aucun POST supplémentaire n'est envoyé.
Cette réconciliation limite les doublons mais ne remplace pas l'idempotence serveur :
une connexion coupée alors que le serveur travaille encore, ou plusieurs onglets
concurrents, peuvent laisser une ambiguïté. Aucun retry automatique.

Le brouillon est conservé en mémoire tant que la page reste ouverte ; il n'est pas
stocké sur disque et disparaît en quittant/rechargeant la page. Une requête déjà
envoyée peut néanmoins se terminer côté serveur après navigation ; le prochain GET
retrouve alors l'échange. Une panne initiale de GET est distinguée d'un historique
vide et bloque l'envoi jusqu'au rétablissement de la lecture.

Le transcript défile vers la réponse seulement si la lecture est proche du bas ;
sinon un bouton permet de rejoindre les derniers échanges. La réduction des
animations est respectée. « Conversation locale » et le volet de confidentialité
expliquent le fonctionnement avec les seules catégories de contexte ; aucun prompt,
identifiant de mémoire, score brut ou objet SQL n'est exposé.

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

Pour autoriser un échange réel avec Ollama depuis le navigateur (plusieurs minutes
possibles au premier chargement) :

```powershell
$env:PSYCHOSPACE_REAL_CHAT = '1'
npx playwright test tests/browser/companion.spec.js
Remove-Item Env:PSYCHOSPACE_REAL_CHAT
```

Les autres tests Compagnon simulent explicitement les cas vide, erreur, attente,
réponse perdue et resynchronisation dans le navigateur de test uniquement. L'application
ne contient aucun message simulé. Le test réel vérifie la réponse, la persistance
par GET, les trois états de présence et affiche la durée ressentie côté interface.

Validation locale du 23 septembre 2026 : POST réel depuis le Compagnon, réponse 200
en 223,08 s côté interface (chargement initial inclus), deux messages confirmés par
GET. Modèle inchangé et timeout backend configuré à 300 s uniquement dans le
processus serveur de démonstration. Les trois états de présence ont été vérifiés.
Build réussi, 12 tests unitaires et 16 tests navigateur réussis ; le test d'écriture
réelle de check-in est resté désactivé pour cette phase.
