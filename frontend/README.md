# PsychoSpace · Foundation UI

Phases 1 à 7B : shell de navigation, présence abstraite, vue d'ensemble, État du jour, Compagnon avec voix locale et microphone conditionnel, Mon évolution, Empreinte de rythme, Mémoire et Accompagnement.
L’interface et les libellés d’accessibilité sont en français, avec dates et nombres
au format français. Les noms techniques et les routes restent inchangés. Le niveau
moderate est formulé « Ton rythme évolue depuis quelques jours. » ; le bouton
« Pourquoi ? » affiche l’explication réelle et le score sous la forme « 62 % ».
Le dossier initial contenait seulement `.gitkeep` ; aucun framework ni style existant.
React 19 + Vite 7, CSS natif, icônes SVG locales et polices système : aucun asset
externe ni CDN à l'exécution.

## Parler à PsychoSpace — Phase 7B

`src/services/speechRecognition.js` utilise exclusivement `window.SpeechRecognition`
avec une propriété native `processLocally` et `available({ langs: ['fr-FR'],
processLocally: true })`. Les API absentes, anciennes ou uniquement préfixées
restent désactivées. Aucune affectation à false et aucun repli vers le cloud.

Le service distingue available, downloadable, downloading et unavailable. Le
pack n'est installé que sur clic explicite avec les mêmes options locales, puis
sa disponibilité est vérifiée à nouveau. Une installation n'ouvre jamais le micro.
Si le navigateur annonce un téléchargement en cours, « Vérifier l’installation »
actualise son état. Une erreur d'installation conserve l'accès au clavier.

« Parler » arrête la synthèse avant de vérifier à nouveau le mode local et de
démarrer la reconnaissance fr-FR ; `start()` déclenche la permission navigateur.
L'état listening dépend de l'événement natif de démarrage. La transcription
intermédiaire reste visible, puis le texte final est ajouté au brouillon existant,
sans envoi automatique. « Arrêter » conserve le texte provisoire disponible à
relire et annule la capture. Quitter Compagnon annule la capture et invalide les
callbacks, y compris pendant une vérification asynchrone de disponibilité.
L'envoi et la lecture sont bloqués pendant la capture ; le champ texte reste
utilisable. Seul un clic Envoyer passe ensuite par le POST chat déjà existant.

Aucun MediaRecorder, fichier audio, transfert audio au backend, mémoire automatique
ou moteur de transcription externe. « Voix traitée sur cet appareil » n'apparaît
que lorsque la disponibilité locale fr-FR est confirmée.

Validation réelle du 23 septembre 2026 : Edge Windows 153, avec et sans fenêtre
visible, expose processLocally, available et install ; `available()` pour fr-FR
renvoie **unavailable**. Aucun pack n'a été installé et aucune capture n'a été
lancée : le bouton est désactivé, le message explicatif affiché et le clavier
reste actif. Aucun résultat de transcription réelle ni cycle complet depuis le
micro ne peut être revendiqué dans cet environnement. Les parcours d'écoute,
permissions, installation et transcription sont vérifiés avec des mocks uniquement
dans les tests. La synthèse Hortense reste indépendante de cette limitation.
Le parcours de secours au clavier a aussi été rejoué réellement avec Ollama :
réponse confirmée par GET, lecture locale Microsoft Hortense fr-FR, événements
start/end et retour attentive validés. Cela ne constitue pas un test microphone.
Validation : 31 tests unitaires, 39 tests navigateur validés sur les exécutions
complète et ciblées, quatre anciens tests d'écriture désactivés, build réussi.

```powershell
$env:PSYCHOSPACE_REAL_MIC = '1'
npx playwright test tests/browser/recognition.spec.js
Remove-Item Env:PSYCHOSPACE_REAL_MIC
```

Ce test ouvre Edge avec une fenêtre visible et rapporte ses capacités natives.
Il ne simule pas une voix humaine et ne force aucun service de reconnaissance.

## Voix de PsychoSpace — Phase 7A

`src/services/voice.js` centralise `speechSynthesis`, la liste actualisée avec
`voiceschanged`, la lecture, l'arrêt, les événements réels et les erreurs. Seules
les voix déclarées `localService === true` sont admissibles : fr-FR, puis autre
français, puis voix locale par défaut (repli signalé en console). Sans voix locale
vérifiable, la lecture reste indisponible plutôt que de laisser le navigateur
choisir implicitement une voix distante. Aucun SDK, clé ou endpoint vocal.

« Réponses vocales » est désactivé par défaut et persiste dans `localStorage`
sous `voiceEnabled`. Charger l'historique, revenir au Compagnon ou cocher la
préférence ne lit aucun texte. Après un nouvel envoi utilisateur, seule la réponse
POST confirmée et présente dans le transcript peut être lue automatiquement.
« Écouter » permet aussi la lecture explicite d'une réponse visible ; « Arrêter »
annule la lecture. Un nouvel envoi, la désactivation ou la sortie du Compagnon
l'arrêtent également. Les callbacks des anciennes lectures sont invalidés.

L'état speaking commence sur l'événement natif `start`, puis revient à attentive
sur `end`, erreur ou annulation. La pulsation est décorative, sans analyse audio,
et disparaît avec `prefers-reduced-motion`. Le texte demeure disponible. Si le
navigateur refuse la lecture automatique après une réponse lente, un message
invite à cliquer « Écouter » ; aucune tentative de contourner cette restriction.

```powershell
$env:PSYCHOSPACE_REAL_VOICE = '1'
npx playwright test tests/browser/voice.spec.js
Remove-Item Env:PSYCHOSPACE_REAL_VOICE
```

Le test réel envoie « Ça va, je suis juste fatigué. » à Ollama et observe la vraie
voix Windows, sans mock, jusqu'à la fin de lecture. Les autres tests utilisent
des doublures de synthèse pour vérifier sélection, arrêt, erreurs, navigation,
préférence et absence d'appels distants. Les événements natifs confirment le
fonctionnement technique ; la qualité perçue dépend de la voix et de la sortie
audio Windows et nécessite une écoute humaine. Aucun accès au microphone.

Validation Windows du 23 septembre 2026 : réponse Ollama réelle lue par
« Microsoft Hortense - French (France) », `fr-FR`, `localService=true`.
Séquence attentive → thinking → speaking → attentive confirmée par les événements
natifs start/end, texte conservé et persistance de la réponse vérifiée par GET.
L'utilisateur a confirmé que la voix était audible et claire en français.
Le rapprochement POST/historique utilise timestamp et contenu, car le POST ne
renvoie pas l'identifiant présent dans le GET. Les réponses successives sont testées.

## Accompagnement — Phase 6

`/#care` lit `GET /api/interventions/ASTRO-001`. Le moment en cours le plus récent
est prioritaire, puis la proposition non terminée la plus récente, puis le dernier
moment terminé. L'historique permet de consulter chaque message original de l'API.
Le tri conserve les microsecondes. Les types, dont les anciens types des seeds,
sont traduits dans `src/care.js`, avec une formulation générique pour les inconnus.

« Ça me va » envoie uniquement `{ accepted: true }` ; « J’ai terminé » envoie
uniquement `{ completed: true }`. L'affichage change après succès du PATCH et
utilise sa réponse. Pendant l'attente, les actions sont bloquées pour éviter les
doubles soumissions. Les erreurs préservent l'état précédent et restent visibles.
« Pas maintenant » masque la proposition localement, avec un bouton pour la
retrouver ; aucun champ de refus ni écriture n'est ajouté. Aucune proposition
n'est créée automatiquement, et aucun drift n'est recalculé.

Le POST est réservé au test de démonstration explicite via l'API, sans formulaire
technique dans l'application. Le test copie le message d'une intervention réelle
dans un nouvel enregistrement à la date de mission, puis accepte et termine
cette seule intervention depuis l'interface. Les originaux sont comparés par GET
avant/après. L'API ne propose pas de DELETE d'intervention : l'enregistrement de
démonstration reste dans l'historique, terminé.

```powershell
$env:PSYCHOSPACE_REAL_CARE = '1'
npx playwright test tests/browser/care.spec.js
Remove-Item Env:PSYCHOSPACE_REAL_CARE
```

Sans cette variable, le cycle d'écriture est ignoré. Les tests de panne et de
réponse différée utilisent des interceptions uniquement dans le navigateur de test.

## Mémoire — Phase 5

`/#memory` lit les souvenirs via `GET /api/memories/ASTRO-001`. La constellation
présente chaque souvenir dans un fragment focusable, avec une étoile dont
l'intensité et la taille varient légèrement selon l'importance. Sur mobile, les
fragments se suivent verticalement. Un dialogue natif assure le focus modal,
Échap et le retour au fragment ; sa fermeture est bloquée pendant l'écriture.

L'ajout comporte catégorie, information, importance de 1 à 10 et confirmation.
Le contrat exige un identifiant client : UUID généré une seule fois à l'ouverture,
avec `source=user` et date issue de l'horloge de mission. Le PUT transmet le contrat
complet en préservant id, user_id, created_at et source. Les libellés et provenances
sont centralisés dans `src/memory.js` ; les valeurs inconnues restent humaines.
L'oubli exige une confirmation explicite. La disparition commence seulement après
le succès du DELETE. Les erreurs conservent les données et le brouillon ; aucune
écriture automatique ni extraction depuis le Compagnon.

Pour le test réel depuis l'interface, exclusivement sur un souvenir temporaire :

```powershell
$env:PSYCHOSPACE_REAL_MEMORY = '1'
npx playwright test tests/browser/memory.spec.js
Remove-Item Env:PSYCHOSPACE_REAL_MEMORY
```

Le test vérifie le POST, le PUT puis le DELETE par GET, et compare intégralement
les six souvenirs originaux avant/après. Sans cette variable, ce cycle est ignoré.
Les simulations d'erreurs et de liste vide existent uniquement dans les tests.

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

## Empreinte de rythme — Phase 4B

Depuis Mon évolution, le bouton « Empreinte de rythme » ouvre une comparaison
organique SVG sans nouvelle route ni bibliothèque. Les mêmes trois GET réels
fournissent la baseline, les check-ins et le dernier drift chronologique.
La fenêtre contient exactement les trois derniers bilans dont le timestamp est
inférieur ou égal à `detected_at` (microsecondes conservées), même si d'autres
bilans plus récents existent. La valeur récente de chaque dimension est leur
moyenne arithmétique, dans l'unité originale. Sans trois bilans complets ou sans
référence positive pour les sept dimensions, l'état insuffisant est présenté.

Le tracé utilise seulement pour le rendu un déplacement borné autour de la
référence : `1 + 0.48 * tanh((valeur - référence) / référence)`. Les positions
angulaires et la silhouette organique sont fixes ; aucune inversion ne classe
les dimensions comme bonnes ou mauvaises. Les valeurs sources restent intactes.
Le contour habituel reste pointillé et le récent continu. Les sept boutons
numérotés donnent au clavier et au toucher les valeurs, unités et explications.
Les anneaux discrets correspondent exclusivement à `affected_signals`.

« Voir le changement » fait évoluer le contour récent en 1,8 seconde, en
conservant la référence visible. « Revenir à la comparaison » termine la
transition. Avec `prefers-reduced-motion`, la comparaison est immédiate, et une
préférence modifiée pendant la transition arrête également le mouvement.
L'explication, la date et l'indice secondaire viennent du drift backend : aucun
calcul de drift, aucune génération Ollama et aucune écriture API sur cette vue.

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
