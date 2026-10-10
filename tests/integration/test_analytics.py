"""Integration tests verifying the required analytical SQL queries."""

from datetime import UTC, datetime
import pytest
from sqlalchemy import create_engine, text
from fleet_pipeline.database import init_db
from fleet_pipeline.load import load_pipeline_data
from fleet_pipeline.models import NormalizedRecord, RejectedRecord, ValidationResult


@pytest.fixture
def analytics_db_engine(tmp_path):
    """Provide a populated test database engine for analytics verification."""
    db_file = tmp_path / "analytics_fleet.db"
    engine = create_engine(f"sqlite:///{db_file}")
    init_db(engine)

    # Insert two days of observations for two vehicles
    day1_early = datetime(2026, 10, 10, 8, 0, 0, tzinfo=UTC)
    day1_late = datetime(2026, 10, 10, 18, 0, 0, tzinfo=UTC)
    day2 = datetime(2026, 10, 11, 9, 0, 0, tzinfo=UTC)

    records = [
        NormalizedRecord(
            source_vehicle_id="bus-01",
            vehicle_name="Line 1 Bus",
            vehicle_type="TransitBus",
            latitude=33.5700,
            longitude=-7.5800,
            observed_at=day1_early,
            source_name="feed",
            source_record_id=NormalizedRecord.generate_surrogate_key(
                "bus-01", day1_early, 33.5700, -7.5800
            ),
        ),
        NormalizedRecord(
            source_vehicle_id="bus-01",
            vehicle_name="Line 1 Bus",
            vehicle_type="TransitBus",
            latitude=33.5850,
            longitude=-7.5950,
            observed_at=day1_late,
            source_name="feed",
            source_record_id=NormalizedRecord.generate_surrogate_key(
                "bus-01", day1_late, 33.5850, -7.5950
            ),
        ),
        NormalizedRecord(
            source_vehicle_id="bus-01",
            vehicle_name="Line 1 Bus",
            vehicle_type="TransitBus",
            latitude=33.6000,
            longitude=-7.6100,
            observed_at=day2,
            source_name="feed",
            source_record_id=NormalizedRecord.generate_surrogate_key(
                "bus-01", day2, 33.6000, -7.6100
            ),
        ),
        NormalizedRecord(
            source_vehicle_id="van-02",
            vehicle_name="Delivery Van",
            vehicle_type="Van",
            latitude=48.8566,
            longitude=2.3522,
            observed_at=day1_early,
            source_name="feed",
            source_record_id=NormalizedRecord.generate_surrogate_key(
                "van-02", day1_early, 48.8566, 2.3522
            ),
        ),
    ]

    rejections = [
        RejectedRecord(
            raw_record={"device": {"id": "bad-1"}},
            issue_code="COORDINATES_OUT_OF_BOUNDS",
            issue_message="Latitude 150 out of bounds",
        ),
        RejectedRecord(
            raw_record={"device": {"id": ""}},
            issue_code="MISSING_VEHICLE_ID",
            issue_message="ID empty",
        ),
    ]

    val_res = ValidationResult(valid_records=records, rejected_records=rejections)
    load_pipeline_data(engine, val_res)

    return engine


def test_query_1_daily_activity(analytics_db_engine):
    """Verify Query 1: count of positions per vehicle and per day."""
    # SQLite compatible date_trunc equivalent:
    # strftime('%Y-%m-%d', observed_at) or SUBSTR(observed_at, 1, 10)
    query = text(
        """
        SELECT
            v.source_vehicle_id,
            SUBSTR(vp.observed_at, 1, 10) AS activity_day,
            COUNT(*) AS position_count
        FROM vehicle_positions vp
        JOIN vehicles v ON vp.vehicle_id = v.vehicle_id
        GROUP BY v.source_vehicle_id, SUBSTR(vp.observed_at, 1, 10)
        ORDER BY activity_day DESC, v.source_vehicle_id;
        """
    )

    with analytics_db_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        # bus-01 has 1 position on day 2 (2026-10-11)
        # bus-01 has 2 positions on day 1 (2026-10-10)
        # van-02 has 1 position on day 1 (2026-10-10)
        assert len(rows) == 3
        # First row: day 2, bus-01
        assert rows[0][0] == "bus-01"
        assert rows[0][1] == "2026-10-11"
        assert rows[0][2] == 1


def test_query_2_latest_position_window_function(analytics_db_engine):
    """Verify Query 2: latest position for each vehicle using ROW_NUMBER()."""
    query = text(
        """
        WITH ranked_positions AS (
            SELECT
                vp.position_id,
                v.source_vehicle_id,
                vp.latitude,
                vp.longitude,
                vp.observed_at,
                ROW_NUMBER() OVER (
                    PARTITION BY vp.vehicle_id
                    ORDER BY vp.observed_at DESC, vp.position_id DESC
                ) AS rank_num
            FROM vehicle_positions vp
            JOIN vehicles v ON vp.vehicle_id = v.vehicle_id
        )
        SELECT source_vehicle_id, latitude, longitude, observed_at
        FROM ranked_positions
        WHERE rank_num = 1
        ORDER BY source_vehicle_id;
        """
    )

    with analytics_db_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        assert len(rows) == 2  # one for bus-01, one for van-02

        # bus-01 latest is day2 (lat=33.6000)
        assert rows[0][0] == "bus-01"
        assert float(rows[0][1]) == pytest.approx(33.6000)

        # van-02 latest is day1 (lat=48.8566)
        assert rows[1][0] == "van-02"
        assert float(rows[1][1]) == pytest.approx(48.8566)


def test_query_3_rejections_by_issue_code(analytics_db_engine):
    """Verify Query 3: count of rejected records grouped by etl_run_id and issue_code."""
    query = text(
        """
        SELECT
            er.etl_run_id,
            dqi.issue_code,
            COUNT(*) AS rejected_count
        FROM data_quality_issues dqi
        JOIN etl_runs er ON dqi.etl_run_id = er.etl_run_id
        GROUP BY er.etl_run_id, dqi.issue_code
        ORDER BY rejected_count DESC;
        """
    )

    with analytics_db_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        assert len(rows) == 2
        issue_codes = {r[1]: r[2] for r in rows}
        assert issue_codes["COORDINATES_OUT_OF_BOUNDS"] == 1
        assert issue_codes["MISSING_VEHICLE_ID"] == 1

