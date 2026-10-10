"""Data validation module enforcing domain rules and separating valid records from rejections."""

import logging
from datetime import UTC, datetime
from typing import Any

from dateutil import parser as date_parser

from fleet_pipeline.models import (
    NormalizedRecord,
    RejectedRecord,
    ValidationResult,
)
from fleet_pipeline.normalize import normalize_record

logger = logging.getLogger("fleet_pipeline.validate")


def validate_single_record(
    raw_item: dict[str, Any],
    source_name: str = "sample_file",
) -> NormalizedRecord | RejectedRecord:
    """Validate a single raw record and return a NormalizedRecord or RejectedRecord.

    Args:
        raw_item: Raw record dictionary.
        source_name: Name of the data source.

    Returns:
        NormalizedRecord on success, or RejectedRecord with detailed issue reason.
    """
    mapped = normalize_record(raw_item, source_name=source_name)

    # 1. Validate source_vehicle_id
    source_vehicle_id = mapped.get("source_vehicle_id")
    if not source_vehicle_id or not str(source_vehicle_id).strip():
        return RejectedRecord(
            raw_record=raw_item,
            issue_code="MISSING_VEHICLE_ID",
            issue_message="Field 'source_vehicle_id' (or device.id) is missing or empty.",
        )

    # 2. Validate latitude & longitude numeric and boundaries
    lat_raw = mapped.get("latitude")
    lon_raw = mapped.get("longitude")

    if lat_raw is None or lon_raw is None:
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=mapped.get("source_record_id"),
            issue_code="MISSING_COORDINATES",
            issue_message="Latitude or longitude coordinate is missing or null.",
        )

    try:
        latitude = float(lat_raw)
        longitude = float(lon_raw)
    except (ValueError, TypeError):
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=mapped.get("source_record_id"),
            issue_code="INVALID_COORDINATES_TYPE",
            issue_message=f"Coordinates cannot be converted to float: lat={lat_raw}, lon={lon_raw}",
        )

    if not (-90.0 <= latitude <= 90.0):
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=mapped.get("source_record_id"),
            issue_code="COORDINATES_OUT_OF_BOUNDS",
            issue_message=f"Latitude {latitude} is outside valid boundary [-90.0, 90.0].",
        )

    if not (-180.0 <= longitude <= 180.0):
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=mapped.get("source_record_id"),
            issue_code="COORDINATES_OUT_OF_BOUNDS",
            issue_message=f"Longitude {longitude} is outside valid boundary [-180.0, 180.0].",
        )

    # 3. Validate observed timestamp
    observed_raw = mapped.get("observed_at_raw")
    if not observed_raw:
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=mapped.get("source_record_id"),
            issue_code="MISSING_TIMESTAMP",
            issue_message="Observation timestamp is missing or empty.",
        )

    try:
        if isinstance(observed_raw, datetime):
            parsed_dt = observed_raw
        else:
            parsed_dt = date_parser.parse(str(observed_raw))

        # Convert or enforce UTC
        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=UTC)
        else:
            parsed_dt = parsed_dt.astimezone(UTC)
    except Exception as exc:
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=mapped.get("source_record_id"),
            issue_code="INVALID_TIMESTAMP_FORMAT",
            issue_message=f"Timestamp '{observed_raw}' is not a valid date format: {exc}",
        )

    # 4. Resolve source_record_id (stable ID or deterministic surrogate key)
    source_record_id = mapped.get("source_record_id")
    if not source_record_id or not str(source_record_id).strip():
        source_record_id = NormalizedRecord.generate_surrogate_key(
            source_vehicle_id=source_vehicle_id,
            observed_at=parsed_dt,
            latitude=latitude,
            longitude=longitude,
        )

    # 5. Build validated NormalizedRecord
    try:
        return NormalizedRecord(
            source_vehicle_id=source_vehicle_id,
            vehicle_name=mapped.get("vehicle_name"),
            vehicle_type=mapped.get("vehicle_type"),
            latitude=latitude,
            longitude=longitude,
            observed_at=parsed_dt,
            source_name=source_name,
            source_record_id=source_record_id,
        )
    except Exception as exc:
        return RejectedRecord(
            raw_record=raw_item,
            source_record_id=source_record_id,
            issue_code="SCHEMA_VALIDATION_ERROR",
            issue_message=f"Pydantic schema validation failed: {exc}",
        )


def validate_records(
    raw_records: list[dict[str, Any]],
    source_name: str = "sample_file",
) -> ValidationResult:
    """Validate a batch of raw records, separating valid items from quality rejections.

    Args:
        raw_records: List of dictionaries extracted from source.
        source_name: Name of the extraction source.

    Returns:
        ValidationResult containing lists of valid and rejected records.
    """
    valid_list: list[NormalizedRecord] = []
    rejected_list: list[RejectedRecord] = []

    for item in raw_records:
        result = validate_single_record(item, source_name=source_name)
        if isinstance(result, NormalizedRecord):
            valid_list.append(result)
        else:
            rejected_list.append(result)

    logger.info(
        "Validation complete: %d total, %d valid, %d rejected",
        len(raw_records),
        len(valid_list),
        len(rejected_list),
    )

    return ValidationResult(
        valid_records=valid_list,
        rejected_records=rejected_list,
    )
