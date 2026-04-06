from __future__ import annotations

import logging


DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def _coerce_level(level_name: str) -> int:
    if not level_name:
        return logging.INFO
    candidate = logging.getLevelName(level_name.upper())
    if isinstance(candidate, int):
        return candidate
    return logging.INFO


def setup_logging(level_name: str) -> logging.Logger:
    """Configure root logging and return the app logger."""
    logging.basicConfig(level=_coerce_level(level_name), format=DEFAULT_LOG_FORMAT)
    return logging.getLogger("lili")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)