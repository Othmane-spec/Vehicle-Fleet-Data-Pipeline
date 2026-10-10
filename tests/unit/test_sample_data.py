"""Tests verifying the actual sample data files (vehicles.json and vehicles.csv)."""

from pathlib import Path

from fleet_pipeline.extract import extract_source
from fleet_pipeline.validate import validate_records


def test_sample_vehicles_json_end_to_end():
    """Verify that data/sample/vehicles.json contains 8 records: 3 valid and 5 rejections."""
    json_path = Path("data/sample/vehicles.json")
    assert json_path.exists()

    raw_records = extract_source(json_path)
    assert len(raw_records) == 8

    result = validate_records(raw_records, source_name="sample_json")
    assert result.total_count == 8
    assert result.valid_count == 3
    assert result.rejected_count == 5

    rejected_codes = [r.issue_code for r in result.rejected_records]
    assert "MISSING_VEHICLE_ID" in rejected_codes
    assert "COORDINATES_OUT_OF_BOUNDS" in rejected_codes
    assert "INVALID_TIMESTAMP_FORMAT" in rejected_codes
    assert "MISSING_COORDINATES" in rejected_codes


def test_sample_vehicles_csv_end_to_end():
    """Verify that data/sample/vehicles.csv is properly extracted and validated."""
    csv_path = Path("data/sample/vehicles.csv")
    assert csv_path.exists()

    raw_records = extract_source(csv_path)
    assert len(raw_records) == 5

    result = validate_records(raw_records, source_name="sample_csv")
    assert result.total_count == 5
    assert result.valid_count == 2
    assert result.rejected_count == 3

    rejected_codes = [r.issue_code for r in result.rejected_records]
    assert "MISSING_VEHICLE_ID" in rejected_codes
    assert "COORDINATES_OUT_OF_BOUNDS" in rejected_codes
    assert "INVALID_TIMESTAMP_FORMAT" in rejected_codes
