# Technical Decisions

## Python packaging

Le projet utilise `pyproject.toml` comme source de verite pour les dependances et le point d'entree console. L'installation recommandee en developpement est :

```bash
python -m pip install -e ".[dev]"
```

## PostgreSQL comme cible analytique

PostgreSQL est retenu pour rester proche d'un environnement Data Engineering courant tout en restant simple a lancer localement avec Docker Compose.

## SQLite dans les tests d'integration

Les tests d'integration utilisent SQLite pour verifier rapidement les garanties transactionnelles sans dependance externe. Le code de chargement conserve une compatibilite explicite avec PostgreSQL pour l'execution reelle.

## Idempotence

Les chargements repetes ne doivent pas creer de doublons. Les vehicules sont synchronises par `source_vehicle_id`. Les positions sont inserees avec `ON CONFLICT DO NOTHING` sur `source_record_id`.

## Rejets non fatals

Les lignes invalides sont considerees comme des problemes de qualite de donnee, pas comme des erreurs systeme. Elles sont stockees dans un fichier de rejet et dans `data_quality_issues`.

## CI

La CI execute `ruff` sur `src` et `tests`, puis lance toute la suite `pytest`. Les scripts manuels de demonstration a la racine ne sont pas inclus dans la gate de lint.
