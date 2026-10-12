"""Main entry point for the Vehicle Fleet Data Pipeline."""

import logging
import sys

from fleet_pipeline.config import get_settings
from fleet_pipeline.database import check_connection, get_engine, init_db
from fleet_pipeline.extract import extract_source
from fleet_pipeline.load import load_pipeline_data
from fleet_pipeline.logging_config import setup_logging
from fleet_pipeline.rejects import save_rejections
from fleet_pipeline.validate import validate_records

logger = logging.getLogger("fleet_pipeline.main")


def run_pipeline() -> int:
    """Execute the end-to-end ETL pipeline."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting Vehicle Fleet Data Pipeline")

    engine = get_engine()
    if not check_connection(engine):
        logger.error("Database connection failed. Check your .env settings.")
        return 1

    try:
        init_db(engine)
        raw_records = extract_source(settings.resolved_source_path)
        validation_result = validate_records(raw_records, source_name=settings.source_type)
        save_rejections(validation_result.rejected_records, settings.resolved_rejected_dir)
        summary = load_pipeline_data(engine, validation_result)
    except Exception:
        logger.exception("Pipeline failed")
        return 1

    logger.info(
        "Pipeline completed: run_id=%d read=%d loaded=%d rejected=%d",
        summary.etl_run_id,
        summary.rows_read,
        summary.rows_loaded,
        summary.rows_rejected,
    )
    return 0


def main() -> None:
    """Console-script compatible entry point."""
    raise SystemExit(run_pipeline())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
        sys.exit(0)
