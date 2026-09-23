# PsychoSpace · Foundation UI

Phase 1 uniquement : shell de navigation, présence abstraite et Overview connecté.
L’interface et les libellés d’accessibilité sont en français, avec dates et nombres
au format français. Les noms techniques et les routes restent inchangés. Le niveau
moderate est formulé « Ton rythme évolue depuis quelques jours. » ; le bouton
« Pourquoi ? » affiche l’explication réelle et le score sous la forme « 62 % ».
Le dossier initial contenait seulement `.gitkeep` ; aucun framework ni style existant.
React 19 + Vite 7, CSS natif, icônes SVG locales et polices système : aucun asset
externe ni CDN à l'exécution. Pulse, Companion, Evolution, Memory et Care sont des
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
```

Le [proxy Vite](https://vite.dev/config/server-options#server-proxy) centralise cette
destination et relaie `/api` sans changer le backend ni sa politique CORS. Le même
proxy est configuré pour `npm run preview` (port 4173). Un hébergement statique du
build doit fournir son propre reverse proxy `/api` vers FastAPI : cette option
Vite n'est pas un serveur de production. Ne placer aucun secret dans `VITE_*`.

## Données et comportement

`DEMO_USER_ID` est centralisé dans `src/config.js`. `src/api.js` appelle uniquement
les quatre GET profile, baseline, drift et checkins. Aucun POST, génération Ollama
ou écriture SQLite. L'accueil utilise le prénom reçu et l'heure locale du navigateur.
Le dernier drift est sélectionné par detected_at UTC, microsecondes comprises,
puis id ; aucune détection ou modification des scores côté UI. Un score 0.62 est
affiché 62 % uniquement dans le panneau ouvert par « Show me why », avec un libellé
explicite : ce n'est ni un risque médical ni un diagnostic.

Sleep, Energy, Fatigue et Activity comparent le **dernier check-in** à la baseline,
sans moyenne récente implicite. Les barres sont décoratives, normalisées par
indicateur, et leurs valeurs sont aussi textuelles. La date de la dernière saisie
et la mention des données de démonstration rendent visibles les dates fictives de
2080 : elles ne sont pas présentées comme la journée réelle de l'utilisateur.
Une absence de drift ne signifie pas que le moteur a confirmé une stabilité.
Baseline absente : tirets et indication explicite. Profil absent : vue vide.

`PsychoSpacePresence` accepte idle, thinking, attentive et drift ; seuls idle et
drift sont utilisés ici. L'événement résolu laisse la présence idle. Les variations
du halo sont discrètes, sans alarme ni code rouge. Les animations sont désactivées
avec `prefers-reduced-motion`. Liens de navigation nommés, focus clavier visibles,
lien d'évitement, bouton d'explication avec `aria-expanded`, états loading/error/empty.
Une panne réseau ou un délai de 12 secondes affiche un message humain et un bouton
de nouvelle tentative ; aucune erreur technique brute ni donnée de remplacement.

## Vérification

```powershell
npm run build
npm test
# Avec le frontend et le backend démarrés ; Microsoft Edge installé :
npx playwright test
```

Les tests navigateur utilisent le vrai backend pour Alex, les valeurs du drift,
les quatre métriques et la navigation. Seuls les scénarios panne/vide/chargement
interceptent les réponses réseau. Tests desktop, tablette 768 px, mobile 390 px,
clavier, réduction des animations et absence de requêtes externes. Captures dans
`test-results/` (ignoré par Git). Sur un poste sans Edge, adapter `channel` dans
`playwright.config.js` au navigateur Playwright installé.
