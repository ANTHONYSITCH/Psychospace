# Containerisation et exécution locale

Ce dépôt fournit une configuration pour exécuter PostgreSQL en conteneur et le script ETL `etl` qui insère des données de démonstration.

Fichiers clés:
- `docker-compose.yml` : configuration du service `db` (Postgres).
- `.env.example` : variables d'environnement à copier en `.env`.
- `requirements.txt` : dépendances Python nécessaires pour exécuter `etl`.

Ports:
- Hôte `DB_PORT` (défini dans `.env`) -> Conteneur `5432`.

Prérequis:
- Docker Desktop installé et démarré sur Windows.
- Python 3.11+ (ou compatible) si vous exécutez l'ETL localement.

Installation et exécution (Windows PowerShell):

1. Copier les variables d'environnement:

```powershell
copy .env.example .env
```

2. Démarrer le service PostgreSQL:

```powershell
docker compose up -d
```

3. Vérifier l'état du conteneur:

```powershell
docker compose ps
docker compose logs -f db
```

4. Créer un environnement Python et installer les dépendances:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

5. Lancer le script ETL (après que le conteneur PostgreSQL soit prêt):

```powershell
python etl
```

6. Arrêter et supprimer les conteneurs et volumes:

```powershell
docker compose down -v
```

Dépannage:
- Si `docker compose up -d` échoue, assurez-vous que Docker Desktop est démarré.
- Si le port `DB_PORT` est déjà pris, changez sa valeur dans `.env`.
- Le script `etl` récupère la configuration DB depuis les variables d'environnement: `DB_HOST`, `DB_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.

Sécurité:
- Ne pas committer le fichier `.env` contenant des mots de passe réels.

Support:
- Dites-moi si vous voulez que j'exécute le script ETL ici une fois Docker démarré, ou que j'ajoute un service `backend` lié au conteneur Postgres.

