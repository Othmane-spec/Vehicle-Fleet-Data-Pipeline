"""Unit tests for validation, surrogate key generation and rejection handling."""

from datetime import UTC, datetime
from pathlib import Path

from fleet_pipeline.models import NormalizedRecord
from fleet_pipeline.rejects import save_rejections
from fleet_pipeline.validate import validate_records, validate_single_record


def test_validate_single_valid_record():
    """Verify valid record is converted to NormalizedRecord with UTC timestamp."""
    raw = {
        "device": {"id": "v-1", "name": "Bus 1", "vehicleType": "Bus"},
        "position": {
            "latitude": 33.5731,
            "longitude": -7.5898,
            "timestamp": "2026-10-10T10:30:00+02:00",
        },
    }
    result = validate_single_record(raw, source_name="test_feed")

    assert isinstance(result, NormalizedRecord)
    assert result.source_vehicle_id == "v-1"
    assert result.latitude == 33.5731
    assert result.longitude == -7.5898
    assert result.observed_at.tzinfo == UTC
    assert result.observed_at.hour == 8  # 10:30 +02:00 -> 08:30 UTC
    assert result.source_record_id is not None
    assert len(result.source_record_id) == 64  # SHA-256 hex length


def test_surrogate_key_is_deterministic():
    """Verify that identical attributes generate the exact same surrogate key."""
    dt = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
    key1 = NormalizedRecord.generate_surrogate_key("v-100", dt, 48.8566, 2.3522)
    key2 = NormalizedRecord.generate_surrogate_key("v-100", dt, 48.8566, 2.3522)
    key3 = NormalizedRecord.generate_surrogate_key("v-100", dt, 48.8567, 2.3522)

    assert key1 == key2
    assert key1 != key3


def test_validate_missing_vehicle_id():
    """Verify rejection when source_vehicle_id is missing or blank."""
    raw = {
        "device": {"id": "   ", "name": "Nameless"},
        "position": {"latitude": 33.5, "longitude": -7.5, "timestamp": "2026-10-10T10:00:00Z"},
    }
    rejected = validate_single_record(raw)
    assert rejected.issue_code == "MISSING_VEHICLE_ID"


def test_validate_latitude_out_of_bounds():
    """Verify rejection when latitude exceeds 90 degrees."""
    raw = {
        "device": {"id": "v-1"},
        "position": {"latitude": 92.5, "longitude": 0.0, "timestamp": "2026-10-10T10:00:00Z"},
    }
    rejected = validate_single_record(raw)
    assert rejected.issue_code == "COORDINATES_OUT_OF_BOUNDS"
    assert "Latitude 92.5" in rejected.issue_message


def test_validate_longitude_out_of_bounds():
    """Verify rejection when longitude exceeds 180 degrees."""
    raw = {
        "device": {"id": "v-1"},
        "position": {"latitude": 45.0, "longitude": -195.0, "timestamp": "2026-10-10T10:00:00Z"},
    }
    rejected = validate_single_record(raw)
    assert rejected.issue_code == "COORDINATES_OUT_OF_BOUNDS"


def test_validate_missing_coordinates():
    """Verify rejection when coordinates are null or missing."""
    raw = {
        "device": {"id": "v-1"},
        "position": {"latitude": None, "longitude": 10.0, "timestamp": "2026-10-10T10:00:00Z"},
    }
    rejected = validate_single_record(raw)
    assert rejected.issue_code == "MISSING_COORDINATES"


def test_validate_invalid_timestamp():
    """Verify rejection when timestamp is malformed."""
    raw = {
        "device": {"id": "v-1"},
        "position": {"latitude": 33.5, "longitude": -7.5, "timestamp": "not-a-timestamp"},
    }
    rejected = validate_single_record(raw)
    assert rejected.issue_code == "INVALID_TIMESTAMP_FORMAT"


def test_validate_records_batch_separation():
    """Verify validate_records processes a batch and separates valid from rejected."""
    batch = [
        {
            "device": {"id": "good-1"},
            "position": {"latitude": 33.5, "longitude": -7.5, "timestamp": "2026-10-10T10:00:00Z"},
        },
        {
            "device": {"id": "bad-1"},
            "position": {"latitude": 120.0, "longitude": -7.5, "timestamp": "2026-10-10T10:00:00Z"},
        },
        {
            "device": {"id": "good-2"},
            "position": {"latitude": 34.0, "longitude": -7.0, "timestamp": "2026-10-10T10:05:00Z"},
        },
    ]
    res = validate_records(batch, source_name="batch_test")

    assert res.total_count == 3
    assert res.valid_count == 2
    assert res.rejected_count == 1
    assert res.rejected_records[0].issue_code == "COORDINATES_OUT_OF_BOUNDS"


def test_save_rejections_creates_file(tmp_path: Path):
    """Verify save_rejections writes JSON file to disk."""
    raw = {"device": {"id": ""}, "position": {"latitude": 0, "longitude": 0}}
    rejected = validate_single_record(raw)

    out_file = save_rejections([rejected], output_dir=tmp_path)
    assert out_file is not None
    assert out_file.exists()
    assert "rejections_" in out_file.name

    # Empty list returns None
    assert save_rejections([], output_dir=tmp_path) is None
