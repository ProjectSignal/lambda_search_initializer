import logging
import os
from typing import Any


def get_logger(name: str) -> Any:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Configure logging level
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logger.level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(handler)

    return logger