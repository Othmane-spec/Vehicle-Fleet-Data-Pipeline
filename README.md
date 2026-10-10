# 🚗 Vehicle Fleet Data Pipeline

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/postgres-15+-blue.svg)
![Pydantic](https://img.shields.io/badge/pydantic-v2-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

## 📌 Présentation du Projet

Ce projet est un pipeline de données (ETL) de bout en bout conçu pour collecter, normaliser, valider et ingérer des données de télémétrie de véhicules dans un entrepôt de données PostgreSQL. 

L'objectif principal est de transformer des données brutes et hétérogènes (provenant de fichiers JSON ou CSV) en tables analytiques fiables, tout en garantissant une qualité de donnée stricte et une idempotence totale.

## 🏗️ Architecture Technique

Le pipeline suit une architecture modulaire basée sur les principes de séparation des responsabilités :

### Flux de Données (ETL)
1. **Extraction** : Lecture automatique de fichiers JSON/CSV avec gestion des erreurs fatales.
2. **Normalisation** : Mapping des champs sources variés vers un schéma standard unique.
3. **Validation** : Contrôle rigoureux des types, des bornes GPS (Latitude/Longitude) et des formats de date (UTC).
4. **Gestion des Rejets** : Isolation des enregistrements invalides dans des fichiers de rejet avec motifs d'erreur détaillés.
5. **Chargement** : Ingestion dans PostgreSQL avec mécanisme de `UPSERT` pour éviter les doublons.

### Stack Technique
- **Langage** : Python 3.11+
- **Validation & Settings** : Pydantic & Pydantic-Settings
- **Base de données** : PostgreSQL
- **Tests** : Pytest
- **Gestion des dates** : python-dateutil

## 📊 Modèle de Données

Le projet implémente un schéma relationnel optimisé pour le suivi et l'analyse :
- `etl_runs` : Historique et statistiques de chaque exécution du pipeline.
- `vehicles` : Référentiel unique des véhicules de la flotte.
- `vehicle_positions` : Historique des positions GPS liées aux véhicules.
- `data_quality_issues` : Audit détaillé des lignes rejetées pour analyse de qualité.

## 🚀 Installation et Lancement

### Prérequis
- Python 3.11 ou supérieur
- Une instance PostgreSQL active

### Configuration
1. Clonez le dépôt :
   ```bash
   git clone https://github.com/votre-utilisateur/vehicle-fleet-data-pipeline.git
   cd "Vehicle Fleet Data Pipeline"
   ```

2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Configurez vos variables d'environnement dans un fichier `.env` :
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=fleet_warehouse
   POSTGRES_USER=fleet_app
   POSTGRES_PASSWORD=votre_mot_de_passe
   SOURCE_FILE=data/sample/vehicles.json
   REJECTED_DIR=data/rejected
   ```

### Exécution
Pour lancer le pipeline :
```bash
python -m fleet_pipeline.main
```

Pour lancer les tests unitaires :
```bash
pytest tests/
```

## 🛠️ Roadmap (V2)
- [ ] Intégration d'une API REST pour l'extraction des données.
- [ ] Mise en place de **dbt Core** pour les transformations SQL analytiques.
- [ ] Orchestration avec **Apache Airflow**.
- [ ] Conteneurisation complète avec **Docker Compose**.
- [ ] CI/CD via **GitHub Actions**.

## 📄 Licence
Ce projet est sous licence MIT.
