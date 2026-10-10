-- =====================================================================
-- Analytical SQL Queries for Vehicle Fleet Data Pipeline
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Nombre de positions par véhicule et par jour
-- ---------------------------------------------------------------------
-- Calcule le volume d'activité quotidienne pour chaque véhicule.
SELECT
    v.vehicle_id,
    v.source_vehicle_id,
    v.vehicle_name,
    DATE_TRUNC('day', vp.observed_at) AS activity_day,
    COUNT(*) AS position_count
FROM vehicle_positions vp
JOIN vehicles v ON vp.vehicle_id = v.vehicle_id
GROUP BY
    v.vehicle_id,
    v.source_vehicle_id,
    v.vehicle_name,
    DATE_TRUNC('day', vp.observed_at)
ORDER BY
    activity_day DESC,
    position_count DESC,
    v.vehicle_id;


-- ---------------------------------------------------------------------
-- 2. Dernière position connue de chaque véhicule
-- ---------------------------------------------------------------------
-- Utilise une fonction de fenêtrage ROW_NUMBER().
-- Gestion explicite des horodatages identiques : en cas d'égalité sur observed_at,
-- le tie-breaker est position_id DESC (dernier identifiant inséré dans la base).
WITH ranked_positions AS (
    SELECT
        vp.position_id,
        vp.source_record_id,
        vp.vehicle_id,
        v.source_vehicle_id,
        v.vehicle_name,
        v.vehicle_type,
        vp.latitude,
        vp.longitude,
        vp.observed_at,
        vp.ingested_at,
        vp.source_name,
        ROW_NUMBER() OVER (
            PARTITION BY vp.vehicle_id
            ORDER BY vp.observed_at DESC, vp.position_id DESC
        ) AS rank_num
    FROM vehicle_positions vp
    JOIN vehicles v ON vp.vehicle_id = v.vehicle_id
)
SELECT
    vehicle_id,
    source_vehicle_id,
    vehicle_name,
    vehicle_type,
    latitude,
    longitude,
    observed_at,
    ingested_at,
    source_record_id,
    source_name
FROM ranked_positions
WHERE rank_num = 1
ORDER BY vehicle_id;


-- ---------------------------------------------------------------------
-- 3. Nombre de positions rejetées par exécution et par motif
-- ---------------------------------------------------------------------
-- Permet de surveiller la qualité de la donnée ingérée par exécution ETL.
SELECT
    er.etl_run_id,
    er.started_at AS run_started_at,
    er.status AS run_status,
    dqi.issue_code,
    COUNT(*) AS rejected_count,
    MIN(dqi.detected_at) AS first_detected_at,
    MAX(dqi.detected_at) AS last_detected_at
FROM data_quality_issues dqi
JOIN etl_runs er ON dqi.etl_run_id = er.etl_run_id
GROUP BY
    er.etl_run_id,
    er.started_at,
    er.status,
    dqi.issue_code
ORDER BY
    er.etl_run_id DESC,
    rejected_count DESC;
