"""Module responsible for persisting rejected records to disk with detailed issue motives."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fleet_pipeline.models import RejectedRecord

logger = logging.getLogger("fleet_pipeline.rejects")


def save_rejections(
    rejected_records: list[RejectedRecord],
    output_dir: Path | str,
    prefix: str = "rejections",
) -> Path | None:
    """Save rejected records into a timestamped JSON file.

    Args:
        rejected_records: List of RejectedRecord instances.
        output_dir: Target directory path where rejection file will be stored.
        prefix: Filename prefix.

    Returns:
        Path to the generated JSON file if records were saved, or None if list was empty.
    """
    if not rejected_records:
        logger.info("No rejected records to persist.")
        return None

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    file_name = f"{prefix}_{timestamp_str}.json"
    file_path = out_path / file_name

    serializable = [record.model_dump(mode="json") for record in rejected_records]

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)

    logger.warning(
        "Persisted %d rejected records with error motives to %s",
        len(rejected_records),
        file_path,
    )
    return file_path
