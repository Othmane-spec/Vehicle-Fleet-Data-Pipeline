-- =====================================================================
-- DDL Schema for Vehicle Fleet Data Pipeline (PostgreSQL)
-- Ordre de création strict pour respecter les contraintes de clés étrangères :
-- 1. etl_runs (aucune FK)
-- 2. vehicles (aucune FK)
-- 3. vehicle_positions (FK -> vehicles, FK -> etl_runs)
-- 4. data_quality_issues (FK -> etl_runs)
-- =====================================================================

-- 1. Table d'observabilité des exécutions du pipeline
CREATE TABLE IF NOT EXISTS etl_runs (
    etl_run_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    rows_read INTEGER NOT NULL DEFAULT 0,
    rows_loaded INTEGER NOT NULL DEFAULT 0,
    rows_rejected INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

-- 2. Table dimensionnelle des véhicules
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id BIGSERIAL PRIMARY KEY,
    source_vehicle_id VARCHAR(100) UNIQUE NOT NULL,
    vehicle_name VARCHAR(255),
    vehicle_type VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour les recherches par identifiant source
CREATE INDEX IF NOT EXISTS idx_vehicles_source_id ON vehicles (source_vehicle_id);

-- 3. Table de faits des positions géographiques observées
CREATE TABLE IF NOT EXISTS vehicle_positions (
    position_id BIGSERIAL PRIMARY KEY,
    source_record_id VARCHAR(128) UNIQUE NOT NULL,
    vehicle_id BIGINT NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    latitude NUMERIC(9,6) NOT NULL CHECK (latitude BETWEEN -90.0 AND 90.0),
    longitude NUMERIC(9,6) NOT NULL CHECK (longitude BETWEEN -180.0 AND 180.0),
    observed_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_name VARCHAR(100) NOT NULL,
    etl_run_id BIGINT NOT NULL REFERENCES etl_runs(etl_run_id) ON DELETE CASCADE
);

-- Index composites et de performance pour les analyses
CREATE INDEX IF NOT EXISTS idx_positions_vehicle_observed ON vehicle_positions (vehicle_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_observed_at ON vehicle_positions (observed_at);
CREATE INDEX IF NOT EXISTS idx_positions_etl_run ON vehicle_positions (etl_run_id);

-- 4. Table d'audit des rejets et anomalies de qualité de données
CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id BIGSERIAL PRIMARY KEY,
    etl_run_id BIGINT NOT NULL REFERENCES etl_runs(etl_run_id) ON DELETE CASCADE,
    source_record_id VARCHAR(128),
    issue_code VARCHAR(100) NOT NULL,
    issue_message TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour les agrégations d'anomalies
CREATE INDEX IF NOT EXISTS idx_dq_issues_run_id ON data_quality_issues (etl_run_id);
CREATE INDEX IF NOT EXISTS idx_dq_issues_code ON data_quality_issues (issue_code);

