"""Logging configuration for the vehicle fleet pipeline."""

import logging
import sys


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure application-wide structured logging.

    Args:
        log_level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').

    Returns:
        Root logger configured for the application.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] [run_id=%(run_id)s] %(message)s"

    class RunIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            if not hasattr(record, "run_id"):
                record.run_id = "default"
            return True

    logger = logging.getLogger("fleet_pipeline")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        handler.addFilter(RunIdFilter())
        logger.addHandler(handler)

    return logger
