"""Data extraction module for local JSON and CSV files."""

import csv
import json
import logging
from pathlib import Path
from typing import Any

from fleet_pipeline.models import FatalExtractionError

logger = logging.getLogger("fleet_pipeline.extract")


def extract_from_json(file_path: Path | str) -> list[dict[str, Any]]:
    """Extract records from a local JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        List of raw dictionaries extracted from the file.

    Raises:
        FatalExtractionError: If the file is missing, unreadable, or not valid JSON.
    """
    path = Path(file_path)

    if not path.exists():
        raise FatalExtractionError(f"Source file does not exist: {path}")

    if not path.is_file():
        raise FatalExtractionError(f"Source path is not a file: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            content = json.load(f)
    except json.JSONDecodeError as exc:
        raise FatalExtractionError(f"Malformed JSON syntax in file {path}: {exc}") from exc
    except OSError as exc:
        raise FatalExtractionError(f"I/O error while reading {path}: {exc}") from exc

    if isinstance(content, list):
        records = [item for item in content if isinstance(item, dict)]
        logger.info("Successfully extracted %d records from JSON file %s", len(records), path)
        return records
    elif isinstance(content, dict):
        logger.info("Successfully extracted 1 record from JSON object %s", path)
        return [content]
    else:
        raise FatalExtractionError(
            f"Invalid JSON root structure in {path}: "
            f"expected array or object, got {type(content).__name__}"
        )


def extract_from_csv(file_path: Path | str) -> list[dict[str, Any]]:
    """Extract records from a local CSV file.

    Args:
        file_path: Path to the CSV file.

    Returns:
        List of raw dictionaries extracted from the file.

    Raises:
        FatalExtractionError: If the file is missing, unreadable, or malformed.
    """
    path = Path(file_path)

    if not path.exists():
        raise FatalExtractionError(f"Source file does not exist: {path}")

    if not path.is_file():
        raise FatalExtractionError(f"Source path is not a file: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = [dict(row) for row in reader]
    except csv.Error as exc:
        raise FatalExtractionError(f"CSV parsing error in file {path}: {exc}") from exc
    except OSError as exc:
        raise FatalExtractionError(f"I/O error while reading {path}: {exc}") from exc

    logger.info("Successfully extracted %d records from CSV file %s", len(records), path)
    return records


def extract_source(file_path: Path | str) -> list[dict[str, Any]]:
    """Auto-detect file format based on extension and extract records.

    Args:
        file_path: Path to the JSON or CSV file.

    Returns:
        List of raw dictionaries.

    Raises:
        FatalExtractionError: If file format is unsupported or file cannot be extracted.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        return extract_from_json(path)
    elif suffix in (".csv", ".txt"):
        return extract_from_csv(path)
    else:
        raise FatalExtractionError(f"Unsupported file extension '{suffix}' for source file: {path}")
