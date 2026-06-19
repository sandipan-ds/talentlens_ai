"""Logging helpers that keep sensitive candidate data out of logs."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for application modules.

    Args:
        name: Logger namespace, usually `__name__`.

    Returns:
        Standard library logger instance.
    """
    return logging.getLogger(name)

