# Architecture

## Objectif

Le projet implemente un pipeline ETL local pour des donnees de flotte automobile. Il lit des fichiers JSON ou CSV, normalise les champs, valide les donnees, isole les rejets, puis charge les lignes valides et les metadonnees d'execution dans PostgreSQL.

## Flux ETL

1. `extract.py` lit la source locale et transforme le contenu en liste de dictionnaires Python.
2. `normalize.py` mappe les formats source vers un contrat commun.
3. `validate.py` applique les regles qualite et produit un `ValidationResult`.
4. `rejects.py` persiste les rejets dans `data/rejected`.
5. `load.py` execute le chargement transactionnel vers la base.
6. `sql/analytics.sql` contient les requetes d'analyse attendues.

## Garanties

- Les erreurs d'extraction sont fatales.
- Les erreurs de qualite ligne par ligne ne bloquent pas le traitement des lignes valides.
- Le chargement est idempotent avec `source_vehicle_id` et `source_record_id`.
- Les operations de chargement sont transactionnelles.
- Les executions sont auditees dans `etl_runs`.
- Les rejets sont audites dans `data_quality_issues`.

## Execution locale

Le point d'entree applicatif est `fleet-pipeline`, expose par `pyproject.toml`. Le pipeline cree le schema si necessaire, puis traite le fichier configure par `SOURCE_FILE`.

## Execution conteneurisee

`compose.yaml` fournit une instance PostgreSQL et un service `pipeline`. La base est persistante via un volume Docker nomme `postgres_data`.
