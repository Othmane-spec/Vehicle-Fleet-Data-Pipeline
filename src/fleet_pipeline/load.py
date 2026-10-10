"""Transactional database loading with idempotency and audit metadata tracking."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, Engine, text

from fleet_pipeline.models import NormalizedRecord, RejectedRecord, ValidationResult

logger = logging.getLogger("fleet_pipeline.load")


@dataclass(frozen=True)
class LoadSummary:
    """Summary of data loading stage execution."""

    etl_run_id: int
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    status: str
    started_at: datetime
    finished_at: datetime


def create_etl_run(conn: Connection) -> int:
    """Create a new record in etl_runs with RUNNING status.

    Args:
        conn: Active SQLAlchemy connection.

    Returns:
        Generated etl_run_id.
    """
    now = datetime.now(UTC)
    query = text(
        """
        INSERT INTO etl_runs (started_at, status, rows_read, rows_loaded, rows_rejected)
        VALUES (:started_at, 'RUNNING', 0, 0, 0)
        RETURNING etl_run_id;
        """
    )
    result = conn.execute(query, {"started_at": now})
    row = result.fetchone()
    if row is None:
        raise RuntimeError("Failed to retrieve generated etl_run_id from database.")
    etl_run_id = int(row[0])
    logger.info("Created ETL run with ID: %d", etl_run_id)
    return etl_run_id


def finish_etl_run(
    conn: Connection,
    etl_run_id: int,
    status: str,
    rows_read: int,
    rows_loaded: int,
    rows_rejected: int,
    error_message: str | None = None,
) -> None:
    """Update etl_runs table with completion status and metrics.

    Args:
        conn: Active SQLAlchemy connection.
        etl_run_id: Identifier of the run.
        status: Final status ('SUCCESS' or 'FAILED').
        rows_read: Total count of records processed.
        rows_loaded: Count of positions successfully loaded.
        rows_rejected: Count of invalid records rejected.
        error_message: Optional error message if failed.
    """
    now = datetime.now(UTC)
    query = text(
        """
        UPDATE etl_runs
        SET finished_at = :finished_at,
            status = :status,
            rows_read = :rows_read,
            rows_loaded = :rows_loaded,
            rows_rejected = :rows_rejected,
            error_message = :error_message
        WHERE etl_run_id = :etl_run_id;
        """
    )
    conn.execute(
        query,
        {
            "finished_at": now,
            "status": status,
            "rows_read": rows_read,
            "rows_loaded": rows_loaded,
            "rows_rejected": rows_rejected,
            "error_message": error_message,
            "etl_run_id": etl_run_id,
        },
    )
    logger.info(
        "Finished ETL run %d: status=%s, loaded=%d, rejected=%d",
        etl_run_id,
        status,
        rows_loaded,
        rows_rejected,
    )


def upsert_vehicles(conn: Connection, valid_records: list[NormalizedRecord]) -> dict[str, int]:
    """Idempotently insert or update vehicles.

    Returns a mapping of source_vehicle_id -> vehicle_id.

    Args:
        conn: Active SQLAlchemy connection.
        valid_records: List of normalized records to extract vehicles from.

    Returns:
        Dictionary mapping source_vehicle_id to internal vehicle_id.
    """
    if not valid_records:
        return {}

    # Deduplicate vehicles within the current batch to avoid conflict in the same statement
    distinct_vehicles: dict[str, dict[str, Any]] = {}
    for rec in valid_records:
        distinct_vehicles[rec.source_vehicle_id] = {
            "source_vehicle_id": rec.source_vehicle_id,
            "vehicle_name": rec.vehicle_name,
            "vehicle_type": rec.vehicle_type,
        }

    now = datetime.now(UTC)
    upsert_stmt = text(
        """
        INSERT INTO vehicles (source_vehicle_id, vehicle_name, vehicle_type, updated_at)
        VALUES (:source_vehicle_id, :vehicle_name, :vehicle_type, :updated_at)
        ON CONFLICT (source_vehicle_id) DO UPDATE SET
            vehicle_name = COALESCE(EXCLUDED.vehicle_name, vehicles.vehicle_name),
            vehicle_type = COALESCE(EXCLUDED.vehicle_type, vehicles.vehicle_type),
            updated_at = :updated_at;
        """
    )

    for veh in distinct_vehicles.values():
        conn.execute(
            upsert_stmt,
            {
                "source_vehicle_id": veh["source_vehicle_id"],
                "vehicle_name": veh["vehicle_name"],
                "vehicle_type": veh["vehicle_type"],
                "updated_at": now,
            },
        )

    # Fetch vehicle IDs
    source_ids = list(distinct_vehicles.keys())
    lookup_stmt = text("SELECT source_vehicle_id, vehicle_id FROM vehicles;")
    rows = conn.execute(lookup_stmt).fetchall()
    id_map = {row[0]: int(row[1]) for row in rows if row[0] in source_ids}

    logger.info("Synchronized %d vehicles in database", len(id_map))
    return id_map


def load_positions(
    conn: Connection,
    valid_records: list[NormalizedRecord],
    vehicle_id_map: dict[str, int],
    etl_run_id: int,
) -> int:
    """Insert vehicle positions idempotently (ON CONFLICT DO NOTHING).

    Args:
        conn: Active SQLAlchemy connection.
        valid_records: List of validated records.
        vehicle_id_map: Map of source_vehicle_id -> vehicle_id.
        etl_run_id: Current ETL run ID.

    Returns:
        Number of newly inserted position rows.
    """
    if not valid_records:
        return 0

    now = datetime.now(UTC)
    insert_stmt = text(
        """
        INSERT INTO vehicle_positions (
            source_record_id, vehicle_id, latitude, longitude,
            observed_at, ingested_at, source_name, etl_run_id
        ) VALUES (
            :source_record_id, :vehicle_id, :latitude, :longitude,
            :observed_at, :ingested_at, :source_name, :etl_run_id
        )
        ON CONFLICT (source_record_id) DO NOTHING;
        """
    )

    rows_inserted = 0
    for rec in valid_records:
        vehicle_id = vehicle_id_map.get(rec.source_vehicle_id)
        if vehicle_id is None:
            logger.error("Missing vehicle_id mapping for %s", rec.source_vehicle_id)
            continue

        result = conn.execute(
            insert_stmt,
            {
                "source_record_id": rec.source_record_id,
                "vehicle_id": vehicle_id,
                "latitude": rec.latitude,
                "longitude": rec.longitude,
                "observed_at": rec.observed_at,
                "ingested_at": now,
                "source_name": rec.source_name,
                "etl_run_id": etl_run_id,
            },
        )
        if result.rowcount > 0:
            rows_inserted += result.rowcount

    logger.info("Inserted %d positions (out of %d candidates)", rows_inserted, len(valid_records))
    return rows_inserted


def record_quality_issues(
    conn: Connection,
    rejected_records: list[RejectedRecord],
    etl_run_id: int,
) -> int:
    """Insert data quality issues into data_quality_issues table.

    Args:
        conn: Active SQLAlchemy connection.
        rejected_records: List of rejected records.
        etl_run_id: Current ETL run ID.

    Returns:
        Count of issues recorded.
    """
    if not rejected_records:
        return 0

    insert_stmt = text(
        """
        INSERT INTO data_quality_issues (
            etl_run_id, source_record_id, issue_code, issue_message, detected_at
        ) VALUES (
            :etl_run_id, :source_record_id, :issue_code, :issue_message, :detected_at
        );
        """
    )

    for item in rejected_records:
        conn.execute(
            insert_stmt,
            {
                "etl_run_id": etl_run_id,
                "source_record_id": item.source_record_id,
                "issue_code": item.issue_code,
                "issue_message": item.issue_message,
                "detected_at": item.detected_at,
            },
        )

    logger.info("Recorded %d data quality issues for run %d", len(rejected_records), etl_run_id)
    return len(rejected_records)


def load_pipeline_data(
    engine: Engine,
    validation_result: ValidationResult,
) -> LoadSummary:
    """Execute complete transactional load with idempotency and audit tracking.

    Args:
        engine: Database engine.
        validation_result: Container of valid and rejected records.

    Returns:
        LoadSummary with final execution metrics.
    """
    started_at = datetime.now(UTC)

    with engine.begin() as conn:
        etl_run_id = create_etl_run(conn)

        try:
            # 1. Upsert vehicles
            vehicle_id_map = upsert_vehicles(conn, validation_result.valid_records)

            # 2. Idempotent insert positions
            rows_loaded = load_positions(
                conn=conn,
                valid_records=validation_result.valid_records,
                vehicle_id_map=vehicle_id_map,
                etl_run_id=etl_run_id,
            )

            # 3. Record quality issues
            record_quality_issues(
                conn=conn,
                rejected_records=validation_result.rejected_records,
                etl_run_id=etl_run_id,
            )

            # 4. Finalize run status as SUCCESS
            finish_etl_run(
                conn=conn,
                etl_run_id=etl_run_id,
                status="SUCCESS",
                rows_read=validation_result.total_count,
                rows_loaded=rows_loaded,
                rows_rejected=validation_result.rejected_count,
            )

            finished_at = datetime.now(UTC)

            return LoadSummary(
                etl_run_id=etl_run_id,
                rows_read=validation_result.total_count,
                rows_loaded=rows_loaded,
                rows_rejected=validation_result.rejected_count,
                status="SUCCESS",
                started_at=started_at,
                finished_at=finished_at,
            )

        except Exception as exc:
            logger.error("Transactional load failed for run %d: %s", etl_run_id, exc, exc_info=True)
            try:
                finish_etl_run(
                    conn=conn,
                    etl_run_id=etl_run_id,
                    status="FAILED",
                    rows_read=validation_result.total_count,
                    rows_loaded=0,
                    rows_rejected=validation_result.rejected_count,
                    error_message=str(exc),
                )
            except Exception:
                pass
            raise
