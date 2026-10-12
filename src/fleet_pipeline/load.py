"""Transactional database loading with idempotency and audit tracking."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, Engine, bindparam, text

from fleet_pipeline.models import NormalizedRecord, RejectedRecord, ValidationResult

logger = logging.getLogger("fleet_pipeline.load")


@dataclass(frozen=True)
class LoadSummary:
    """Summary of a database loading stage execution."""

    etl_run_id: int
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    status: str
    started_at: datetime
    finished_at: datetime


def _is_sqlite(conn: Connection) -> bool:
    return conn.dialect.name == "sqlite"


def create_etl_run(conn: Connection) -> int:
    """Create a RUNNING row in etl_runs and return its generated ID."""
    now = datetime.now(UTC)

    if _is_sqlite(conn):
        conn.execute(
            text(
                """
                INSERT INTO etl_runs (
                    started_at, status, rows_read, rows_loaded, rows_rejected
                ) VALUES (
                    :started_at, 'RUNNING', 0, 0, 0
                );
                """
            ),
            {"started_at": now},
        )
        etl_run_id = conn.execute(text("SELECT last_insert_rowid();")).scalar_one()
    else:
        result = conn.execute(
            text(
                """
                INSERT INTO etl_runs (
                    started_at, status, rows_read, rows_loaded, rows_rejected
                ) VALUES (
                    :started_at, 'RUNNING', 0, 0, 0
                )
                RETURNING etl_run_id;
                """
            ),
            {"started_at": now},
        )
        etl_run_id = result.scalar_one()

    logger.info("Created ETL run with ID: %s", etl_run_id)
    return int(etl_run_id)


def finish_etl_run(
    conn: Connection,
    etl_run_id: int,
    status: str,
    rows_read: int,
    rows_loaded: int,
    rows_rejected: int,
    error_message: str | None = None,
) -> None:
    """Update etl_runs with completion status and metrics."""
    conn.execute(
        text(
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
        ),
        {
            "finished_at": datetime.now(UTC),
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


def _distinct_vehicles(valid_records: list[NormalizedRecord]) -> dict[str, dict[str, Any]]:
    """Return the last seen vehicle attributes for each source vehicle ID."""
    vehicles: dict[str, dict[str, Any]] = {}
    for record in valid_records:
        vehicles[record.source_vehicle_id] = {
            "source_vehicle_id": record.source_vehicle_id,
            "vehicle_name": record.vehicle_name,
            "vehicle_type": record.vehicle_type,
        }
    return vehicles


def upsert_vehicles(conn: Connection, valid_records: list[NormalizedRecord]) -> dict[str, int]:
    """Insert or update vehicles idempotently and return source ID -> vehicle_id."""
    vehicles = _distinct_vehicles(valid_records)
    if not vehicles:
        return {}

    updated_at = datetime.now(UTC)
    upsert_stmt = text(
        """
        INSERT INTO vehicles (
            source_vehicle_id, vehicle_name, vehicle_type, updated_at
        ) VALUES (
            :source_vehicle_id, :vehicle_name, :vehicle_type, :updated_at
        )
        ON CONFLICT (source_vehicle_id) DO UPDATE SET
            vehicle_name = COALESCE(EXCLUDED.vehicle_name, vehicles.vehicle_name),
            vehicle_type = COALESCE(EXCLUDED.vehicle_type, vehicles.vehicle_type),
            updated_at = :updated_at;
        """
    )

    for vehicle in vehicles.values():
        conn.execute(upsert_stmt, {**vehicle, "updated_at": updated_at})

    lookup_stmt = text(
        """
        SELECT source_vehicle_id, vehicle_id
        FROM vehicles
        WHERE source_vehicle_id IN :source_vehicle_ids;
        """
    ).bindparams(bindparam("source_vehicle_ids", expanding=True))
    if _is_sqlite(conn):
        rows = conn.execute(text("SELECT source_vehicle_id, vehicle_id FROM vehicles;")).fetchall()
    else:
        rows = conn.execute(
            lookup_stmt,
            {"source_vehicle_ids": tuple(vehicles.keys())},
        ).fetchall()

    vehicle_id_map = {row[0]: int(row[1]) for row in rows if row[0] in vehicles}
    if len(vehicle_id_map) != len(vehicles):
        missing = sorted(set(vehicles) - set(vehicle_id_map))
        raise RuntimeError(f"Missing vehicle IDs after upsert: {missing}")

    logger.info("Synchronized %d vehicles", len(vehicle_id_map))
    return vehicle_id_map


def load_positions(
    conn: Connection,
    valid_records: list[NormalizedRecord],
    vehicle_id_map: dict[str, int],
    etl_run_id: int,
) -> int:
    """Insert positions idempotently and return the number of newly inserted rows."""
    if not valid_records:
        return 0

    ingested_at = datetime.now(UTC)
    insert_stmt = text(
        """
        INSERT INTO vehicle_positions (
            source_record_id,
            vehicle_id,
            latitude,
            longitude,
            observed_at,
            ingested_at,
            source_name,
            etl_run_id
        ) VALUES (
            :source_record_id,
            :vehicle_id,
            :latitude,
            :longitude,
            :observed_at,
            :ingested_at,
            :source_name,
            :etl_run_id
        )
        ON CONFLICT (source_record_id) DO NOTHING;
        """
    )

    inserted = 0
    for record in valid_records:
        vehicle_id = vehicle_id_map.get(record.source_vehicle_id)
        if vehicle_id is None:
            raise RuntimeError(f"Missing vehicle_id for {record.source_vehicle_id}")

        result = conn.execute(
            insert_stmt,
            {
                "source_record_id": record.source_record_id,
                "vehicle_id": vehicle_id,
                "latitude": record.latitude,
                "longitude": record.longitude,
                "observed_at": record.observed_at,
                "ingested_at": ingested_at,
                "source_name": record.source_name,
                "etl_run_id": etl_run_id,
            },
        )
        inserted += max(result.rowcount or 0, 0)

    logger.info("Inserted %d new positions from %d candidates", inserted, len(valid_records))
    return inserted


def record_quality_issues(
    conn: Connection,
    rejected_records: list[RejectedRecord],
    etl_run_id: int,
) -> int:
    """Insert rejected records into data_quality_issues."""
    if not rejected_records:
        return 0

    insert_stmt = text(
        """
        INSERT INTO data_quality_issues (
            etl_run_id,
            source_record_id,
            issue_code,
            issue_message,
            detected_at
        ) VALUES (
            :etl_run_id,
            :source_record_id,
            :issue_code,
            :issue_message,
            :detected_at
        );
        """
    )

    for record in rejected_records:
        conn.execute(
            insert_stmt,
            {
                "etl_run_id": etl_run_id,
                "source_record_id": record.source_record_id,
                "issue_code": record.issue_code,
                "issue_message": record.issue_message,
                "detected_at": record.detected_at,
            },
        )

    logger.info("Recorded %d data quality issues", len(rejected_records))
    return len(rejected_records)


def load_data(
    conn: Connection,
    etl_run_id: int,
    valid_records: list[NormalizedRecord],
    rejected_records: list[RejectedRecord],
) -> int:
    """Load valid records and quality issues inside an existing transaction."""
    vehicle_id_map = upsert_vehicles(conn, valid_records)
    loaded_rows = load_positions(conn, valid_records, vehicle_id_map, etl_run_id)
    record_quality_issues(conn, rejected_records, etl_run_id)
    return loaded_rows


def _record_failed_run(
    engine: Engine,
    validation_result: ValidationResult,
    error_message: str,
) -> None:
    """Best-effort failure audit written outside the rolled-back load transaction."""
    try:
        with engine.begin() as conn:
            etl_run_id = create_etl_run(conn)
            finish_etl_run(
                conn=conn,
                etl_run_id=etl_run_id,
                status="FAILED",
                rows_read=validation_result.total_count,
                rows_loaded=0,
                rows_rejected=validation_result.rejected_count,
                error_message=error_message,
            )
    except Exception:
        logger.exception("Unable to persist FAILED ETL audit row")


def load_pipeline_data(engine: Engine, validation_result: ValidationResult) -> LoadSummary:
    """Run the complete transactional load with idempotency and audit metadata."""
    started_at = datetime.now(UTC)

    try:
        with engine.begin() as conn:
            etl_run_id = create_etl_run(conn)
            rows_loaded = load_data(
                conn=conn,
                etl_run_id=etl_run_id,
                valid_records=validation_result.valid_records,
                rejected_records=validation_result.rejected_records,
            )
            finish_etl_run(
                conn=conn,
                etl_run_id=etl_run_id,
                status="SUCCESS",
                rows_read=validation_result.total_count,
                rows_loaded=rows_loaded,
                rows_rejected=validation_result.rejected_count,
            )
    except Exception as exc:
        _record_failed_run(engine, validation_result, str(exc))
        raise

    return LoadSummary(
        etl_run_id=etl_run_id,
        rows_read=validation_result.total_count,
        rows_loaded=rows_loaded,
        rows_rejected=validation_result.rejected_count,
        status="SUCCESS",
        started_at=started_at,
        finished_at=datetime.now(UTC),
    )
