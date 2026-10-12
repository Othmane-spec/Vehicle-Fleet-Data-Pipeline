# Vehicle Fleet Data Pipeline

Pipeline ETL Python pour collecter, normaliser, valider et charger des donnees de telemetrie de vehicules dans PostgreSQL.

Le projet est pense comme un portfolio Data Engineering junior : il couvre l'extraction JSON/CSV, la validation qualite, la gestion des rejets, l'idempotence, le chargement transactionnel, les requetes analytiques, les tests automatises, Docker Compose et une CI GitHub Actions.

## Stack

- Python 3.11+
- Pydantic v2 et pydantic-settings
- SQLAlchemy 2
- PostgreSQL 15+
- Pytest
- Ruff
- Docker Compose

## Architecture

Flux principal :

1. Extraction depuis `data/sample/vehicles.json` ou `data/sample/vehicles.csv`.
2. Normalisation des champs source vers un schema commun.
3. Validation des identifiants, coordonnees GPS et timestamps UTC.
4. Sauvegarde des lignes invalides dans `data/rejected`.
5. Chargement PostgreSQL transactionnel et idempotent.
6. Audit des executions et des problemes qualite.
7. Requetes analytiques dans `sql/analytics.sql`.

Documentation complementaire :

- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [Technical decisions](docs/decisions.md)

## Modele de donnees

- `etl_runs` : historique des executions ETL.
- `vehicles` : referentiel des vehicules.
- `vehicle_positions` : positions GPS valides.
- `data_quality_issues` : anomalies et rejets de qualite.

## Installation locale

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copier la configuration d'exemple :

```bash
Copy-Item .env.example .env
```

Variables principales :

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fleet_warehouse
POSTGRES_USER=fleet_app
POSTGRES_PASSWORD=change_me
SOURCE_TYPE=file
SOURCE_FILE=data/sample/vehicles.json
REJECTED_DIR=data/rejected
```

## Lancement avec Docker Compose

Demarrer PostgreSQL :

```bash
docker compose up -d postgres
```

Executer le pipeline dans un conteneur :

```bash
docker compose --profile run up --build pipeline
```

Arreter les services :

```bash
docker compose down
```

Supprimer aussi les donnees PostgreSQL locales :

```bash
docker compose down -v
```

## Lancement local

Avec PostgreSQL deja disponible et `.env` configure :

```bash
fleet-pipeline
```

Equivalent module Python :

```bash
python -m fleet_pipeline.main
```

## Tests et qualite

```bash
python -m pytest
python -m ruff check src tests
```

La CI GitHub Actions execute les memes controles sur chaque pull request et sur les pushes vers `main` ou `master`.

## Requetes analytiques

Le fichier `sql/analytics.sql` contient :

- nombre de positions par vehicule et par jour ;
- derniere position connue par vehicule ;
- nombre de rejets par execution et par motif.

## Roadmap

- API REST comme source additionnelle.
- dbt Core pour les transformations analytiques.
- Orchestration Airflow.
- Tests PostgreSQL reels en CI via service container.
