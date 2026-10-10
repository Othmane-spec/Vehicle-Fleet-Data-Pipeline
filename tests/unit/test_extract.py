"""Unit tests for data extraction module."""

from pathlib import Path

import pytest

from fleet_pipeline.extract import (
    extract_from_csv,
    extract_from_json,
    extract_source,
)
from fleet_pipeline.models import FatalExtractionError


def test_extract_json_valid_file(sample_json_path: Path):
    """Test extracting from a valid JSON array file."""
    records = extract_from_json(sample_json_path)
    assert isinstance(records, list)
    assert len(records) == 4
    assert records[0]["device"]["id"] == "bus-001"


def test_extract_json_single_object(tmp_path: Path):
    """Test extracting a single JSON object (returns list of 1)."""
    single_file = tmp_path / "single.json"
    single_file.write_text('{"device": {"id": "single-1"}}', encoding="utf-8")

    records = extract_from_json(single_file)
    assert len(records) == 1
    assert records[0]["device"]["id"] == "single-1"


def test_extract_csv_valid_file(tmp_path: Path):
    """Test extracting from a valid CSV file."""
    csv_file = tmp_path / "vehicles.csv"
    csv_file.write_text(
        "device_id,device_name,latitude,longitude,timestamp\n"
        "veh-1,Bus 1,33.57,-7.58,2026-10-10T10:00:00Z\n"
        "veh-2,Van 2,33.58,-7.59,2026-10-10T10:05:00Z\n",
        encoding="utf-8",
    )

    records = extract_from_csv(csv_file)
    assert len(records) == 2
    assert records[0]["device_id"] == "veh-1"
    assert records[1]["device_name"] == "Van 2"


def test_extract_missing_file_raises_fatal():
    """Ensure a missing file raises FatalExtractionError."""
    with pytest.raises(FatalExtractionError, match="does not exist"):
        extract_from_json("data/sample/does_not_exist.json")


def test_extract_corrupted_json_raises_fatal(tmp_path: Path):
    """Ensure malformed JSON syntax raises FatalExtractionError."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ unclosed json: ", encoding="utf-8")

    with pytest.raises(FatalExtractionError, match="Malformed JSON syntax"):
        extract_from_json(bad_file)


def test_extract_source_unsupported_extension(tmp_path: Path):
    """Ensure unsupported file extension raises FatalExtractionError."""
    unsupported_file = tmp_path / "data.xml"
    unsupported_file.write_text("<data></data>", encoding="utf-8")

    with pytest.raises(FatalExtractionError, match="Unsupported file extension"):
        extract_source(unsupported_file)
