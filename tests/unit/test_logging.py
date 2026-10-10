"""Unit tests for logging configuration."""

import logging

from fleet_pipeline.logging_config import setup_logging


def test_setup_logging_creates_logger():
    """Verify setup_logging configures logger with handler and filter."""
    logger = setup_logging(log_level="DEBUG")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1

    # Verify run_id attribute handling
    record = logging.LogRecord(
        name="fleet_pipeline.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    for handler in logger.handlers:
        for f in handler.filters:
            f.filter(record)
    assert hasattr(record, "run_id")
    assert record.run_id == "default"
