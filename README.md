# Documentation - Psychospace (Base de données + ETL)

But
: Fournir une base de données PostgreSQL containerisée et un pipeline ETL (`etl`) qui insère des jeux de données de démonstration.

Contenu du dépôt
- `docker-compose.yml` : service `db` (Postgres) et volume de persistance.
- `.env.example` : variables d'environnement à dupliquer en `.env`.
- `etl` : script Python qui génère/nettoie des données et les insère en base.
- `requirements.txt` : dépendances Python nécessaires pour exécuter l'ETL.

Prérequis
- Windows 10/11 avec Docker Desktop installé et démarré (ou une instance Docker Engine accessible).
- Python 3.10+ recommandé pour exécuter `etl` localement.

Variables d'environnement (fichier `.env`)
- `DB_HOST` : hôte PostgreSQL (par défaut `db` pour docker-compose, `localhost` pour instance locale)
- `DB_PORT` : port mappé sur l'hôte (ex. `5432`)
- `POSTGRES_DB` : nom de la base (ex. `psychospace_db`)
- `POSTGRES_USER` : utilisateur Postgres
- `POSTGRES_PASSWORD` : mot de passe Postgres

Sécurité: ne commitez jamais un `.env` avec des secrets.

Exemples d'utilisation

1) Préparer les variables d'environnement

```powershell
copy .env.example .env
# Éditez .env pour ajuster DB_HOST/DB_PORT si nécessaire
```

2) Démarrer PostgreSQL via Docker Compose

```powershell
docker compose up -d
```

3) Vérifier que le conteneur est prêt

```powershell
docker compose ps
docker compose logs -f db
```

4) (Optionnel) Vérifier la base depuis l'hôte

Si `psql` est installé:

```powershell
psql "host=$env:DB_HOST port=$env:DB_PORT dbname=$env:POSTGRES_DB user=$env:POSTGRES_USER"
```

Ou via Docker (si le conteneur tourne):

```powershell
docker exec -it $(docker compose ps -q db) psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB
```

5) Installer les dépendances Python et exécuter l'ETL

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
python etl
```

Comportement attendu
- Le script `etl` génère des données de démonstration, les nettoie, et effectue des `INSERT` dans les tables attendues (`missions`, `astronauts`, `daily_checkins`, `sensors`, `sensor_readings`).

Vérifications et sécurité
- Le script `etl` lit la configuration DB depuis les variables d'environnement. Assurez-vous que `DB_HOST` et `DB_PORT` pointent vers la bonne instance.
- J'ai analysé le code: aucun `DROP` / `TRUNCATE` massif ni suppression de fichiers automatique détectés. Le script effectue uniquement des `INSERT`.

Dépannage fréquent
- Erreur "pipe introuvable" / Docker inaccessible: redémarrez Docker Desktop.
- Si `docker compose up -d` bloque sur le téléchargement d'image, vérifiez la connexion réseau et l'accès à Docker Hub.
- Si `psycopg2` pose problème à l'installation: utilisez `psycopg2-binary` (déjà listé dans `requirements.txt`).

Étapes suivantes que je peux effectuer pour vous
- Démarrer le conteneur ici et exécuter l'ETL (je peux le faire dès que Docker Engine est accessible).
- Ajouter un service `backend` connecté à la base si vous voulez déployer l'application complète.

Historique des modifications
- README transformé en documentation d'usage (installation, exécution, dépannage).

Contact
- Répondez ici et je lance/diagnostique les étapes restantes sur votre machine.

