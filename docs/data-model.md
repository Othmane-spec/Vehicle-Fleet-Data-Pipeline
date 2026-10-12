# Data Model

## `etl_runs`

Table d'observabilite des executions.

- `etl_run_id` : cle primaire.
- `started_at` et `finished_at` : bornes temporelles du run.
- `status` : `RUNNING`, `SUCCESS` ou `FAILED`.
- `rows_read`, `rows_loaded`, `rows_rejected` : compteurs de controle.
- `error_message` : message d'erreur en cas d'echec.

## `vehicles`

Dimension des vehicules.

- `vehicle_id` : cle primaire technique.
- `source_vehicle_id` : identifiant metier unique.
- `vehicle_name`, `vehicle_type` : attributs descriptifs.
- `created_at`, `updated_at` : suivi de synchronisation.

## `vehicle_positions`

Table de faits des positions GPS.

- `source_record_id` : cle naturelle unique de position.
- `vehicle_id` : reference vers `vehicles`.
- `latitude`, `longitude` : coordonnees controlees par contraintes SQL.
- `observed_at` : horodatage source normalise UTC.
- `ingested_at` : horodatage d'insertion.
- `etl_run_id` : run ayant insere la position.

## `data_quality_issues`

Audit des lignes rejetees.

- `etl_run_id` : run concerne.
- `source_record_id` : identifiant de ligne si disponible.
- `issue_code` : motif machine-readable.
- `issue_message` : detail lisible.
- `detected_at` : horodatage de detection.

## Idempotence

- `vehicles.source_vehicle_id` evite les doublons de vehicules.
- `vehicle_positions.source_record_id` evite les doublons de positions.
- Quand la source ne fournit pas d'identifiant de position, le pipeline genere un SHA-256 deterministe a partir du vehicule, de l'horodatage UTC et des coordonnees.
