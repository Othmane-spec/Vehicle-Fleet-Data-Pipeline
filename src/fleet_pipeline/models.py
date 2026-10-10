"""Domain models, validation schemas and custom exceptions."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FatalExtractionError(Exception):
    """Fatal error raised when source data cannot be extracted (missing file, syntax error)."""

    pass


class ConfigurationError(Exception):
    """Fatal error raised when configuration parameters are invalid."""

    pass


class NormalizedRecord(BaseModel):
    """Clean, typed and validated record ready for downstream consumption."""

    model_config = ConfigDict(frozen=True)

    source_vehicle_id: str = Field(
        ..., min_length=1, description="Source vehicle business identifier"
    )
    vehicle_name: str | None = Field(default=None, description="Descriptive vehicle name")
    vehicle_type: str | None = Field(default=None, description="Vehicle category/type")
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees [-90, 90]"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees [-180, 180]"
    )
    observed_at: datetime = Field(..., description="Observation timestamp normalized to UTC")
    source_name: str = Field(default="unknown", description="Name of the extraction source")
    source_record_id: str = Field(..., min_length=1, description="Unique and stable record key")

    @field_validator("observed_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure observation timestamp has UTC timezone."""
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)

    @staticmethod
    def generate_surrogate_key(
        source_vehicle_id: str,
        observed_at: datetime,
        latitude: float,
        longitude: float,
    ) -> str:
        """Generate a deterministic surrogate key using SHA-256 hash.

        Formula: sha256(source_vehicle_id | observed_at_iso | latitude | longitude)
        """
        iso_ts = observed_at.astimezone(UTC).isoformat()
        payload = f"{source_vehicle_id.strip()}|{iso_ts}|{latitude:.6f}|{longitude:.6f}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RejectedRecord(BaseModel):
    """Representation of a data record rejected by quality checks."""

    model_config = ConfigDict(frozen=True)

    raw_record: dict[str, Any] = Field(..., description="Original raw record payload")
    source_record_id: str | None = Field(
        default=None, description="Extracted or computed record key"
    )
    issue_code: str = Field(..., min_length=1, description="Machine-readable error code")
    issue_message: str = Field(
        ..., min_length=1, description="Human-readable description of rejection"
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the issue was detected",
    )


class ValidationResult(BaseModel):
    """Aggregate result from the validation and normalization stage."""

    valid_records: list[NormalizedRecord] = Field(default_factory=list)
    rejected_records: list[RejectedRecord] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.valid_records) + len(self.rejected_records)

    @property
    def valid_count(self) -> int:
        return len(self.valid_records)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_records)
