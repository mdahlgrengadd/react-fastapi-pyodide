"""Logging configuration for both Pyodide and CPython environments."""
import logging
import sys
from typing import Any

from .runtime import IS_PYODIDE


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Pyodide-specific logging adjustments
    if IS_PYODIDE:
        # In Pyodide, we want simpler logging
        logging.basicConfig(
            level=level,
            format="%(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# Convenience function for debug logging
def log(*args: Any, **kwargs: Any) -> None:
    """Quick debug logging function."""
    logger = get_logger("app")
    if args:
        logger.info(" ".join(str(arg) for arg in args))
    if kwargs:
        logger.info(str(kwargs))
