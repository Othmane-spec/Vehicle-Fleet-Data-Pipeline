# Projet Data Engineering --- Vehicle Fleet Data Pipeline

## Cahier des charges technique pour un agent de développement

**Version :** 1.0\
**Langue :** Français\
**Objectif :** construire un projet portfolio de Data Engineering de
bout en bout, démontrant l'extraction, la transformation, la validation,
le stockage, l'orchestration et la documentation de données de flotte
automobile.

------------------------------------------------------------------------

## 1. Contexte et objectif

Le projet consiste à créer un pipeline de données qui collecte des
données de véhicules depuis une API REST ou des fichiers JSON/CSV, les
nettoie et les valide, puis les charge dans PostgreSQL afin de produire
des tables analytiques exploitables.

Le projet doit être suffisamment réaliste pour être présenté lors d'un
entretien de **Data Engineer junior**, mais rester réalisable localement
avec des outils gratuits ou open source.

### Objectifs d'apprentissage

-   Programmer un pipeline ETL en Python.
-   Manipuler des données JSON, CSV et tabulaires avec Python et pandas.
-   Utiliser PostgreSQL et écrire du SQL analytique.
-   Concevoir un modèle de données adapté à l'analyse.
-   Ajouter des contrôles de qualité, des logs, une gestion des erreurs
    et des tests.
-   Conteneuriser l'environnement avec Docker Compose.
-   Automatiser les tests avec GitHub Actions.
-   Ajouter dbt Core pour transformer et tester les modèles SQL.
-   Prévoir une orchestration avec Airflow en extension.
-   Documenter l'architecture et les décisions techniques.

### Hors périmètre pour la première version

Ne pas ajouter immédiatement Kafka, Spark, Kubernetes, plusieurs
fournisseurs cloud ou une interface frontend complexe. Ces outils
pourront être envisagés après la réalisation du pipeline principal.

------------------------------------------------------------------------

## 2. Fonctionnalités attendues

### MVP --- version minimale obligatoire

1.  Lire des données depuis un fichier JSON ou CSV local.
2.  Normaliser les champs source.
3.  Valider les coordonnées, les dates, les identifiants et les valeurs
    obligatoires.
4.  Mettre de côté les lignes invalides dans un fichier de rejet.
5.  Charger les données brutes et les données normalisées dans
    PostgreSQL.
6.  Éviter les doublons lors d'une nouvelle exécution.
7.  Produire des logs et un résumé de chaque exécution.
8.  Exécuter des tests automatisés.
9.  Fournir une documentation permettant à une autre personne de lancer
    le projet.

### Version 2 --- amélioration recommandée

-   Extraire les données depuis une API REST.
-   Gérer la pagination, les délais d'attente et les erreurs HTTP.
-   Ajouter dbt Core pour les transformations SQL et les tests.
-   Ajouter une intégration continue avec GitHub Actions.
-   Ajouter une orchestration avec Airflow.
-   Déployer une partie du projet sur un fournisseur cloud, si le budget
    et les accès le permettent.

------------------------------------------------------------------------

## 3. Architecture générale

### Schéma d'architecture

``` mermaid
flowchart TD
    A["Source de données<br/>API REST ou fichiers JSON/CSV"] --> B["Extraction Python"]
    B --> C["Zone brute / Raw"]
    C --> D["Validation et nettoyage<br/>Python + pandas"]
    D --> E{"Données valides ?"}
    E -->|Oui| F["Chargement PostgreSQL"]
    E -->|Non| G["Fichier de rejet<br/>avec motif"]
    F --> H["Transformations SQL / dbt"]
    H --> I["Tables analytiques"]
    I --> J["Requêtes SQL et indicateurs"]
    B --> K["Logs et métadonnées d'exécution"]
    D --> K
    F --> K
    H --> K
    L["Tests pytest / dbt"] -. "vérifient" .-> B
    L -. "vérifient" .-> D
    L -. "vérifient" .-> H
```

### Flux logique

1.  **Extract** : récupérer les données d'une source.
2.  **Raw** : conserver une copie de la réponse ou des données source,
    dans la mesure du possible.
3.  **Validate** : vérifier les champs et les règles métier.
4.  **Transform** : convertir les formats, normaliser les noms et
    calculer les champs nécessaires.
5.  **Load** : écrire les données dans PostgreSQL de façon contrôlée.
6.  **Model** : construire les tables analytiques.
7.  **Test** : tester le code Python, les règles de qualité et les
    modèles SQL.
8.  **Observe** : enregistrer les volumes, erreurs, durées et statuts.

------------------------------------------------------------------------

## 4. Technologies et responsabilités

  -----------------------------------------------------------------------
  Technologie                         Utilisation
  ----------------------------------- -----------------------------------
  Python 3.11+                        Code ETL, validations et
                                      transformations

  pandas                              Manipulation de données tabulaires

  requests ou httpx                   Consommation d'API REST

  PostgreSQL                          Stockage relationnel

  SQL                                 Transformations et analyses

  pytest                              Tests unitaires et d'intégration

  SQLAlchemy ou psycopg               Connexion à PostgreSQL

  Docker / Docker Compose             Environnement reproductible

  dbt Core                            Modélisation SQL, tests et
                                      documentation

  Git / GitHub                        Versioning et collaboration

  GitHub Actions                      Exécution automatique des tests

  Apache Airflow (extension)          Orchestration planifiée

  GCP / AWS / Azure (extension)       Stockage ou entrepôt de données
                                      cloud
  -----------------------------------------------------------------------

**Règle de simplicité :** pour le MVP, choisir une seule bibliothèque de
connexion à PostgreSQL et l'utiliser partout. SQLAlchemy est un choix
raisonnable si le projet utilise également pandas.

------------------------------------------------------------------------

## 5. Modèle de données

### Principes de conception

-   Garder une représentation des données reçues de la source.
-   Séparer les données brutes, les données normalisées et les données
    analytiques.
-   Utiliser une clé source stable pour éviter les doublons.
-   Enregistrer l'heure d'ingestion en UTC.
-   Ne pas supposer que chaque véhicule envoie une position à intervalle
    régulier.
-   Ne pas inventer une position lorsque les coordonnées sont absentes
    ou invalides.
-   Documenter le fuseau horaire et les unités des mesures.

### Schéma relationnel conceptuel

``` mermaid
erDiagram
    VEHICLES ||--o{ VEHICLE_POSITIONS : "possède"
    ETL_RUNS ||--o{ VEHICLE_POSITIONS : "charge"
    ETL_RUNS ||--o{ DATA_QUALITY_ISSUES : "produit"

    VEHICLES {
        bigint vehicle_id PK
        string source_vehicle_id UK
        string vehicle_name
        string vehicle_type
        timestamp created_at
        timestamp updated_at
    }

    VEHICLE_POSITIONS {
        bigint position_id PK
        string source_record_id UK
        bigint vehicle_id FK
        decimal latitude
        decimal longitude
        timestamp observed_at
        timestamp ingested_at
        string source_name
        bigint etl_run_id FK
    }

    ETL_RUNS {
        bigint etl_run_id PK
        timestamp started_at
        timestamp finished_at
        string status
        int rows_read
        int rows_loaded
        int rows_rejected
        string error_message
    }

    DATA_QUALITY_ISSUES {
        bigint issue_id PK
        bigint etl_run_id FK
        string source_record_id
        string issue_code
        string issue_message
        timestamp detected_at
    }
```

### Description des tables

#### `vehicles`

Une ligne par véhicule connu.

  -----------------------------------------------------------------------
  Colonne                 Type conseillé          Description
  ----------------------- ----------------------- -----------------------
  `vehicle_id`            BIGSERIAL / BIGINT      Identifiant interne

  `source_vehicle_id`     VARCHAR                 Identifiant provenant
                                                  de la source, unique

  `vehicle_name`          VARCHAR                 Nom ou libellé du
                                                  véhicule

  `vehicle_type`          VARCHAR                 Type du véhicule

  `created_at`            TIMESTAMPTZ             Date de création

  `updated_at`            TIMESTAMPTZ             Date de mise à jour
  -----------------------------------------------------------------------

#### `vehicle_positions`

Une ligne par position observée.

  -----------------------------------------------------------------------
  Colonne                 Type conseillé          Description
  ----------------------- ----------------------- -----------------------
  `position_id`           BIGSERIAL / BIGINT      Identifiant interne

  `source_record_id`      VARCHAR                 Identifiant stable de
                                                  l'enregistrement,
                                                  unique si disponible

  `vehicle_id`            BIGINT                  Référence vers
                                                  `vehicles`

  `latitude`              NUMERIC(9,6)            Latitude entre -90 et
                                                  90

  `longitude`             NUMERIC(9,6)            Longitude entre -180 et
                                                  180

  `observed_at`           TIMESTAMPTZ             Heure de la position
                                                  dans la source

  `ingested_at`           TIMESTAMPTZ             Heure de chargement
                                                  dans le pipeline

  `source_name`           VARCHAR                 Nom de la source

  `etl_run_id`            BIGINT                  Exécution ayant chargé
                                                  l'enregistrement
  -----------------------------------------------------------------------

**Idempotence :** si la source ne fournit pas d'identifiant de position
stable, définir une clé métier documentée, par exemple véhicule +
horodatage + coordonnées. Évaluer les risques de collisions avant de
l'utiliser.

#### `etl_runs`

Une ligne par exécution du pipeline. Elle permet de connaître le statut
et les volumes traités.

#### `data_quality_issues`

Conserve les erreurs détectées : champ obligatoire absent, date
invalide, coordonnées hors limites, doublon ou format inattendu.

------------------------------------------------------------------------

## 6. Contrat de données source

Le pipeline doit accepter une structure normalisée similaire à celle-ci.
Les noms exacts des champs de la source peuvent varier ; créer une
fonction de mapping plutôt que de disperser les noms de champs dans le
code.

### Exemple JSON d'entrée

``` json
{
  "device": {
    "id": "vehicle-001",
    "name": "Bus 001",
    "vehicleType": "TransitBus"
  },
  "position": {
    "latitude": 33.5731,
    "longitude": -7.5898,
    "timestamp": "2026-10-10T10:30:00Z"
  }
}
```

### Enregistrement normalisé attendu

``` json
{
  "source_vehicle_id": "vehicle-001",
  "vehicle_name": "Bus 001",
  "vehicle_type": "TransitBus",
  "latitude": 33.5731,
  "longitude": -7.5898,
  "observed_at": "2026-10-10T10:30:00Z",
  "source_name": "sample_json"
}
```

### Règles de validation minimales

-   `source_vehicle_id` est obligatoire.
-   La latitude est numérique et comprise entre -90 et 90.
-   La longitude est numérique et comprise entre -180 et 180.
-   `observed_at` doit être une date interprétable avec un fuseau
    horaire défini.
-   Les noms de champs doivent être normalisés.
-   Les doublons doivent être identifiés et traités explicitement.
-   Les champs optionnels peuvent être nuls, mais leur absence doit être
    documentée.
-   Les données invalides sont rejetées avec un code et un message
    explicatif.

------------------------------------------------------------------------

## 7. Organisation du dépôt Git

``` text
vehicle-fleet-data-pipeline/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── compose.yaml
├── docker/
│   └── postgres/
│       └── init.sql
├── data/
│   ├── sample/
│   │   └── vehicles.json
│   └── rejected/
│       └── .gitkeep
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   └── decisions.md
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── src/
│   └── fleet_pipeline/
│       ├── __init__.py
│       ├── config.py
│       ├── logging_config.py
│       ├── extract.py
│       ├── normalize.py
│       ├── validate.py
│       ├── transform.py
│       ├── load.py
│       ├── database.py
│       ├── pipeline.py
│       └── cli.py
├── tests/
│   ├── unit/
│   │   ├── test_normalize.py
│   │   └── test_validate.py
│   ├── integration/
│   │   └── test_load.py
│   └── fixtures/
│       └── sample_vehicles.json
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.example.yml
│   └── models/
│       ├── staging/
│       │   ├── stg_vehicles.sql
│       │   └── schema.yml
│       └── marts/
│           ├── mart_daily_vehicle_activity.sql
│           └── schema.yml
└── .github/
    └── workflows/
        └── tests.yml
```

L'agent peut adapter cette structure si nécessaire, mais il doit
conserver une séparation claire entre extraction, validation,
transformation, chargement, tests et documentation.

------------------------------------------------------------------------

## 8. Déroulement technique du pipeline

``` mermaid
sequenceDiagram
    participant CLI as CLI / Scheduler
    participant EX as Extracteur
    participant VA as Validateur
    participant DB as PostgreSQL
    participant LOG as Logs / ETL Runs

    CLI->>LOG: Créer une exécution
    CLI->>EX: Démarrer l'extraction
    EX-->>CLI: Données source
    CLI->>VA: Normaliser et valider
    VA-->>CLI: Données valides + rejets
    CLI->>DB: Charger véhicules et positions
    DB-->>CLI: Résultat du chargement
    CLI->>LOG: Enregistrer volumes et statut
    CLI-->>CLI: Code de sortie succès/échec
```

### Exigences d'implémentation

1.  La configuration est chargée depuis les variables d'environnement.
2.  Aucun secret ne doit être codé en dur.
3.  Les erreurs d'extraction doivent avoir un message exploitable.
4.  Les insertions en base doivent utiliser des paramètres SQL, jamais
    une concaténation de valeurs utilisateur.
5.  Les chargements doivent être transactionnels lorsque cela est
    adapté.
6.  Les réexécutions ne doivent pas créer de doublons.
7.  Le pipeline doit renvoyer un code de sortie non nul en cas d'échec
    global.
8.  Les logs doivent inclure un identifiant d'exécution.
9.  Les données rejetées ne doivent pas bloquer l'intégralité du
    traitement si la politique de qualité autorise les rejets partiels.
10. Les données sensibles et les tokens d'API ne doivent jamais
    apparaître dans les logs.

------------------------------------------------------------------------

## 9. Stratégie de tests et qualité

### Tests unitaires Python

-   Conversion correcte des champs source.
-   Traitement des champs manquants.
-   Validation des coordonnées.
-   Conversion des dates avec fuseau horaire.
-   Détection des doublons.
-   Gestion des réponses API vides ou mal formées.
-   Comportement correct lors d'une erreur HTTP.

### Tests d'intégration

-   Connexion à PostgreSQL.
-   Création du schéma.
-   Chargement d'un jeu de données valide.
-   Rejet ou journalisation des données invalides.
-   Deuxième exécution sans duplication.
-   Rollback en cas d'erreur de transaction.

### Tests SQL / dbt

-   Clés primaires non nulles et uniques.
-   Clés étrangères cohérentes.
-   Valeurs de latitude et longitude dans les limites.
-   Dates obligatoires présentes.
-   Modèles analytiques cohérents avec les données source.

### Critères de qualité

-   Tests exécutables avec une commande documentée.
-   Pas de secret dans Git.
-   Erreurs documentées et exploitables.
-   Logs compréhensibles.
-   Types et fonctions clairement nommés.
-   README qui permet de reproduire le projet.

------------------------------------------------------------------------

## 10. Requêtes analytiques à fournir

Le projet doit inclure au minimum trois exemples SQL :

1.  Nombre de positions par véhicule et par jour.
2.  Dernière position connue de chaque véhicule.
3.  Nombre de positions rejetées par exécution et par motif.

Exemple de requête pour compter les positions quotidiennes :

``` sql
SELECT
    vehicle_id,
    DATE_TRUNC('day', observed_at) AS activity_day,
    COUNT(*) AS position_count
FROM vehicle_positions
GROUP BY vehicle_id, DATE_TRUNC('day', observed_at)
ORDER BY activity_day DESC, vehicle_id;
```

La requête de dernière position doit utiliser une fonction de fenêtre
telle que `ROW_NUMBER()` ou `DISTINCT ON`, en explicitant la gestion des
horodatages identiques.

------------------------------------------------------------------------

## 11. Docker et configuration

### Services locaux

``` mermaid
flowchart LR
    A["Python ETL<br/>container ou CLI"] --> B["PostgreSQL<br/>container"]
    A --> C["Fichiers sample / rejected"]
    D["pytest"] --> A
    E["dbt Core"] --> B
```

### Variables d'environnement

Fournir un `.env.example` sans secret réel :

``` dotenv
APP_ENV=local
LOG_LEVEL=INFO

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fleet_warehouse
POSTGRES_USER=fleet_app
POSTGRES_PASSWORD=change_me

SOURCE_TYPE=file
SOURCE_FILE=data/sample/vehicles.json
```

En environnement Docker Compose, le nom d'hôte de PostgreSQL sera
généralement le nom du service, par exemple `postgres`, plutôt que
`localhost`.

Ne jamais committer le vrai fichier `.env`. Ajouter `.env`, les
environnements virtuels, caches Python et données privées à
`.gitignore`.

------------------------------------------------------------------------

## 12. Pipeline CI avec GitHub Actions

Le workflow doit :

1.  Installer une version Python supportée.
2.  Installer les dépendances du projet.
3.  Exécuter le lint si un outil de lint est configuré.
4.  Exécuter les tests unitaires.
5.  Lancer les tests d'intégration si un service PostgreSQL est
    configuré dans le workflow.
6.  Exécuter les tests dbt si le projet dbt est inclus et correctement
    configuré.
7.  Échouer clairement si un test échoue.

Ne pas déclarer le workflow réussi si les tests ont été ignorés
silencieusement.

------------------------------------------------------------------------

## 13. Roadmap et définition de terminé

### Phase 1 --- Socle Python

-   [ ] Créer le dépôt et l'environnement Python.
-   [ ] Définir les dépendances.
-   [ ] Créer les exemples de données.
-   [ ] Implémenter extraction fichier, normalisation et validation.
-   [ ] Ajouter les tests unitaires.

**Terminé lorsque :** les données valides et invalides sont distinguées
de manière déterministe et testée.

### Phase 2 --- PostgreSQL et chargement

-   [ ] Créer le schéma SQL.
-   [ ] Ajouter la connexion à PostgreSQL.
-   [ ] Implémenter le chargement transactionnel.
-   [ ] Traiter les doublons et les réexécutions.
-   [ ] Enregistrer les métadonnées d'exécution.

**Terminé lorsque :** le pipeline peut être exécuté deux fois sans
dupliquer les mêmes positions.

### Phase 3 --- Industrialisation

-   [ ] Ajouter Docker Compose.
-   [ ] Ajouter logs structurés et gestion des erreurs.
-   [ ] Ajouter les tests d'intégration.
-   [ ] Ajouter le workflow GitHub Actions.
-   [ ] Rédiger le README et la documentation d'architecture.

**Terminé lorsque :** un développeur qui clone le dépôt peut lancer le
projet en suivant uniquement le README.

### Phase 4 --- Modélisation et cloud

-   [ ] Ajouter dbt Core et les modèles staging/marts.
-   [ ] Ajouter les tests dbt.
-   [ ] Ajouter Airflow uniquement après stabilisation du pipeline.
-   [ ] Déployer un composant cloud si un environnement gratuit
    approprié est disponible.
-   [ ] Documenter les coûts potentiels, les permissions et les limites.

**Terminé lorsque :** le projet explique clairement son flux de données,
ses contrôles de qualité et la façon dont il pourrait être exploité en
environnement réel.

------------------------------------------------------------------------

## 14. Consignes de travail pour l'agent IA

L'agent doit travailler comme un ingénieur Data Engineering senior qui
accompagne un développeur en progression.

### Règles obligatoires

1.  Inspecter le dépôt existant avant de modifier les fichiers.
2.  Ne pas écraser du code existant sans l'avoir compris.
3.  Implémenter le projet progressivement, phase par phase.
4.  Avant chaque phase, annoncer brièvement les fichiers à créer ou
    modifier et pourquoi.
5.  Écrire du code lisible, typé lorsque c'est utile, modulaire et
    testable.
6.  Ajouter les tests en même temps que les fonctionnalités.
7.  Exécuter les tests disponibles après chaque modification
    significative.
8.  Ne jamais inventer le résultat d'une commande ou prétendre qu'un
    test est passé sans l'avoir exécuté.
9.  Ne pas exposer de secrets, tokens, mots de passe ou données privées.
10. Éviter les dépendances inutiles et privilégier les outils open
    source.
11. Ne pas ajouter une technologie avancée simplement pour la mode ;
    justifier sa valeur.
12. Expliquer les choix techniques en français, avec les termes
    techniques anglais lorsque c'est utile.
13. Si une information source est inconnue, créer un exemple synthétique
    et documenter l'hypothèse.
14. Ne pas accéder à une API de production sans autorisation et sans
    configuration explicite.
15. Ne pas lancer de déploiement cloud payant sans confirmation de
    l'utilisateur.

### Mode de collaboration demandé

-   Commencer par analyser l'environnement du dépôt et vérifier Python,
    Docker et PostgreSQL disponibles.
-   Présenter un plan de mise en œuvre court.
-   Attendre une validation avant une refonte importante ou l'ajout de
    services externes.
-   Pour chaque phase, fournir un résumé, les fichiers modifiés, les
    commandes de lancement et les résultats réels des tests.
-   En cas d'erreur, expliquer la cause probable, corriger puis relancer
    les tests pertinents.
-   À la fin, mettre à jour le README et la checklist de progression.

### Première tâche à donner à l'agent

> Analyse le dépôt actuel sans supprimer ni modifier de fichiers.
> Vérifie l'environnement disponible, identifie les éléments déjà
> présents et compare-les à ce cahier des charges. Propose ensuite un
> plan d'implémentation par phases, les dépendances minimales et les
> premières commandes à exécuter. N'implémente rien avant d'avoir
> présenté ce plan.

------------------------------------------------------------------------

## 15. Livrables finaux attendus

Le dépôt doit contenir :

-   Le code Python du pipeline.
-   Le schéma PostgreSQL et les requêtes SQL.
-   Les données synthétiques d'exemple.
-   Les tests unitaires et d'intégration.
-   Les fichiers Docker et la configuration d'environnement exemple.
-   Les modèles dbt et leurs tests, si la phase dbt est terminée.
-   Le workflow CI.
-   Les schémas Mermaid dans la documentation.
-   Un README avec prérequis, installation, exécution, tests,
    architecture et dépannage.
-   Une section « Limites et améliorations futures ».
-   Une démonstration courte et reproductible du pipeline.

## 16. Critère final de réussite

Le projet est réussi si une personne qui découvre le dépôt peut
comprendre le flux de données, lancer le pipeline localement, constater
les données chargées, voir les rejets, exécuter les tests et comprendre
comment le système pourrait évoluer vers un environnement cloud.

**Priorité absolue : un pipeline complet, fiable, testé et bien
documenté avant d'ajouter des technologies distribuées complexes.**
