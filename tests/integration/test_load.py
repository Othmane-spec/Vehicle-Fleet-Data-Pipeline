"""Integration tests for transactional loading, idempotency and audit tracking."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fleet_pipeline.database import init_db
from fleet_pipeline.load import load_pipeline_data
from fleet_pipeline.models import NormalizedRecord, RejectedRecord, ValidationResult


@pytest.fixture
def test_db_engine(tmp_path):
    """Provide a clean test database engine with initialized schema."""
    db_file = tmp_path / "test_fleet.db"
    engine = create_engine(f"sqlite:///{db_file}")
    init_db(engine)
    return engine


@pytest.fixture
def sample_validation_result():
    """Provide a realistic validation result with valid and rejected records."""
    dt1 = datetime(2026, 10, 10, 10, 0, 0, tzinfo=UTC)
    dt2 = datetime(2026, 10, 10, 10, 5, 0, tzinfo=UTC)

    rec1 = NormalizedRecord(
        source_vehicle_id="bus-01",
        vehicle_name="Line 1 Bus",
        vehicle_type="TransitBus",
        latitude=33.5731,
        longitude=-7.5898,
        observed_at=dt1,
        source_name="test_feed",
        source_record_id=NormalizedRecord.generate_surrogate_key("bus-01", dt1, 33.5731, -7.5898),
    )

    rec2 = NormalizedRecord(
        source_vehicle_id="bus-01",
        vehicle_name="Line 1 Bus",
        vehicle_type="TransitBus",
        latitude=33.5800,
        longitude=-7.5950,
        observed_at=dt2,
        source_name="test_feed",
        source_record_id=NormalizedRecord.generate_surrogate_key("bus-01", dt2, 33.5800, -7.5950),
    )

    rec3 = NormalizedRecord(
        source_vehicle_id="van-02",
        vehicle_name="Quick Delivery",
        vehicle_type="DeliveryVan",
        latitude=33.6000,
        longitude=-7.6000,
        observed_at=dt1,
        source_name="test_feed",
        source_record_id=NormalizedRecord.generate_surrogate_key("van-02", dt1, 33.6000, -7.6000),
    )

    rej1 = RejectedRecord(
        raw_record={"device": {"id": ""}, "position": {"latitude": 0, "longitude": 0}},
        issue_code="MISSING_VEHICLE_ID",
        issue_message="Missing vehicle ID",
    )

    return ValidationResult(
        valid_records=[rec1, rec2, rec3],
        rejected_records=[rej1],
    )


def test_first_load_execution(test_db_engine, sample_validation_result):
    """Verify first pipeline execution inserts all valid rows and records metadata."""
    summary = load_pipeline_data(test_db_engine, sample_validation_result)

    assert summary.status == "SUCCESS"
    assert summary.rows_read == 4
    assert summary.rows_loaded == 3
    assert summary.rows_rejected == 1

    with test_db_engine.connect() as conn:
        vehicles_count = conn.execute(text("SELECT COUNT(*) FROM vehicles;")).scalar()
        positions_count = conn.execute(text("SELECT COUNT(*) FROM vehicle_positions;")).scalar()
        runs_count = conn.execute(text("SELECT COUNT(*) FROM etl_runs;")).scalar()
        issues_count = conn.execute(text("SELECT COUNT(*) FROM data_quality_issues;")).scalar()

        assert vehicles_count == 2  # bus-01 and van-02
        assert positions_count == 3
        assert runs_count == 1
        assert issues_count == 1


def test_idempotence_on_second_load(test_db_engine, sample_validation_result):
    """Verify running the exact same data a second time produces NO duplicate records."""
    # First load
    summary1 = load_pipeline_data(test_db_engine, sample_validation_result)
    assert summary1.rows_loaded == 3

    # Second load with identical data
    summary2 = load_pipeline_data(test_db_engine, sample_validation_result)
    assert summary2.rows_loaded == 0  # 0 new positions loaded due to ON CONFLICT DO NOTHING

    with test_db_engine.connect() as conn:
        vehicles_count = conn.execute(text("SELECT COUNT(*) FROM vehicles;")).scalar()
        positions_count = conn.execute(text("SELECT COUNT(*) FROM vehicle_positions;")).scalar()
        runs_count = conn.execute(text("SELECT COUNT(*) FROM etl_runs;")).scalar()

        assert vehicles_count == 2
        assert positions_count == 3
        assert runs_count == 2  # A second run was tracked, but no duplicates inserted


def test_load_rollback_on_error(test_db_engine):
    """Verify transaction rolls back completely when an unexpected database error occurs."""
    dt = datetime(2026, 10, 10, 10, 0, 0, tzinfo=UTC)
    rec = NormalizedRecord(
        source_vehicle_id="fail-veh",
        latitude=33.0,
        longitude=-7.0,
        observed_at=dt,
        source_name="feed",
        source_record_id="valid-key",
    )
    val_res = ValidationResult(valid_records=[rec], rejected_records=[])

    # Drop positions table so load_positions fails mid-transaction
    with test_db_engine.begin() as conn:
        conn.execute(text("DROP TABLE vehicle_positions;"))

    with pytest.raises(Exception):
        load_pipeline_data(test_db_engine, val_res)

    # Verify that vehicles insertion was rolled back
    with test_db_engine.connect() as conn:
        veh_count = conn.execute(
            text("SELECT COUNT(*) FROM vehicles WHERE source_vehicle_id = 'fail-veh';")
        ).scalar()
        failed_runs = conn.execute(
            text("SELECT COUNT(*) FROM etl_runs WHERE status = 'FAILED';")
        ).scalar()
        assert veh_count == 0
        assert failed_runs == 1
