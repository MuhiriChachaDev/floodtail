"""FLOODTAIL — Structured logging configuration.

Provides a single ``setup_logging`` function that configures the root
FLOODTAIL logger with a consistent format, suitable for both console
output during development and future file/handler extension.
"""

import logging
import sys
from typing import Optional

# Canonical logger name for the entire application
LOGGER_NAME = "FLOODTAIL"

# Format:  2026-10-07 09:12:03 | INFO | FLOODTAIL | Configuration loaded
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Configure and return the FLOODTAIL logger.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to INFO if not specified.

    Returns:
        The configured ``logging.Logger`` instance.
    """
    effective_level = getattr(logging, (level or "INFO").upper(), logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(effective_level)

    # Avoid duplicate handlers when called more than once
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(effective_level)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(component: Optional[str] = None) -> logging.Logger:
    """Return a child logger for a specific component.

    Args:
        component: Optional component name (e.g. ``"hazard"``).
                   If omitted, the root FLOODTAIL logger is returned.

    Returns:
        A ``logging.Logger`` scoped to ``FLOODTAIL.<component>``.
    """
    if component:
        return logging.getLogger(f"{LOGGER_NAME}.{component}")
    return logging.getLogger(LOGGER_NAME)
