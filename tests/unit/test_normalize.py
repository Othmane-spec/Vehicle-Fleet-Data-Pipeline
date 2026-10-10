"""Unit tests for data normalization module."""

from fleet_pipeline.normalize import normalize_record


def test_normalize_nested_json():
    """Verify normalization of standard nested JSON."""
    raw = {
        "device": {
            "id": "veh-001",
            "name": "Line 1 Bus",
            "vehicleType": "TransitBus",
        },
        "position": {
            "latitude": 33.5731,
            "longitude": -7.5898,
            "timestamp": "2026-10-10T10:30:00Z",
            "id": "pos-001",
        },
    }
    result = normalize_record(raw, source_name="test_source")

    assert result["source_vehicle_id"] == "veh-001"
    assert result["vehicle_name"] == "Line 1 Bus"
    assert result["vehicle_type"] == "TransitBus"
    assert result["latitude"] == 33.5731
    assert result["longitude"] == -7.5898
    assert result["observed_at_raw"] == "2026-10-10T10:30:00Z"
    assert result["source_record_id"] == "pos-001"
    assert result["source_name"] == "test_source"


def test_normalize_flat_dict():
    """Verify normalization of flat dictionary typical from CSV extraction."""
    raw = {
        "device_id": "truck-99",
        "device_name": "Cargo Hauler",
        "vehicle_type": "SemiTruck",
        "lat": 45.1234,
        "lon": 5.6789,
        "timestamp": "2026-10-10T11:00:00Z",
    }
    result = normalize_record(raw, source_name="csv_source")

    assert result["source_vehicle_id"] == "truck-99"
    assert result["vehicle_name"] == "Cargo Hauler"
    assert result["vehicle_type"] == "SemiTruck"
    assert result["latitude"] == 45.1234
    assert result["longitude"] == 5.6789
    assert result["observed_at_raw"] == "2026-10-10T11:00:00Z"
    assert result["source_record_id"] is None
