"""Data normalization module to map varied source formats into a standard structure."""

from typing import Any


def _get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Retrieve value from a nested dictionary given a key hierarchy."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _first_not_none(*values: Any) -> Any:
    """Return the first value that is not None."""
    for val in values:
        if val is not None:
            if isinstance(val, str) and val.strip() == "":
                continue
            return val
    return None


def normalize_record(raw: dict[str, Any], source_name: str = "sample_file") -> dict[str, Any]:
    """Map raw record keys (nested JSON or flat CSV) into standardized field names.

    Args:
        raw: Raw dictionary from extraction.
        source_name: Name of the extraction source.

    Returns:
        Dictionary with unified keys for validation.
    """
    # 1. Source Vehicle ID
    source_vehicle_id = _first_not_none(
        _get_nested(raw, "device", "id"),
        raw.get("source_vehicle_id"),
        raw.get("device_id"),
        raw.get("vehicle_id"),
    )
    if source_vehicle_id is not None:
        source_vehicle_id = str(source_vehicle_id).strip()

    # 2. Vehicle Name
    vehicle_name = _first_not_none(
        _get_nested(raw, "device", "name"),
        raw.get("vehicle_name"),
        raw.get("device_name"),
        raw.get("name"),
    )
    if vehicle_name is not None:
        vehicle_name = str(vehicle_name).strip()

    # 3. Vehicle Type
    vehicle_type = _first_not_none(
        _get_nested(raw, "device", "vehicleType"),
        _get_nested(raw, "device", "vehicle_type"),
        raw.get("vehicle_type"),
        raw.get("vehicleType"),
    )
    if vehicle_type is not None:
        vehicle_type = str(vehicle_type).strip()

    # 4. Latitude (0.0 is a valid coordinate, cannot use 'or')
    latitude = _first_not_none(
        _get_nested(raw, "position", "latitude"),
        raw.get("latitude"),
        raw.get("lat"),
    )

    # 5. Longitude (0.0 is a valid coordinate, cannot use 'or')
    longitude = _first_not_none(
        _get_nested(raw, "position", "longitude"),
        raw.get("longitude"),
        raw.get("lon"),
        raw.get("lng"),
    )

    # 6. Observed timestamp
    observed_at_raw = _first_not_none(
        _get_nested(raw, "position", "timestamp"),
        raw.get("timestamp"),
        raw.get("observed_at"),
        raw.get("time"),
    )

    # 7. Explicit source record id if provided
    source_record_id = _first_not_none(
        _get_nested(raw, "position", "id"),
        raw.get("source_record_id"),
        raw.get("record_id"),
    )
    if source_record_id is not None:
        source_record_id = str(source_record_id).strip()

    return {
        "source_vehicle_id": source_vehicle_id,
        "vehicle_name": vehicle_name,
        "vehicle_type": vehicle_type,
        "latitude": latitude,
        "longitude": longitude,
        "observed_at_raw": observed_at_raw,
        "source_name": source_name,
        "source_record_id": source_record_id,
        "raw_payload": raw,
    }
