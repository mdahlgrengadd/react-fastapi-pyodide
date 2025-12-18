"""Domain model registry for the Todo demo."""
from app.core.logging import get_logger

logger = get_logger(__name__)

# Import models so SQLAlchemy registers them
try:
    from app.domains.todos.models import Todo
    logger.info("Todo model imported successfully")
except Exception as e:  # pragma: no cover - import-time failure
    logger.error(f"Failed to import Todo model: {e}")
    raise


def configure_relationships() -> bool:
    """Configure SQLAlchemy mappers (kept for parity with older setup)."""
    try:
        from sqlalchemy.orm import configure_mappers

        configure_mappers()
        logger.info("SQLAlchemy mappers configured")
        return True
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Error configuring SQLAlchemy relationships: {e}")
        return False


__all__ = ["Todo", "configure_relationships"]
