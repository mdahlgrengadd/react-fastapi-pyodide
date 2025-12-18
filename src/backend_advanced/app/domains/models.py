"""
Import all domain models to ensure they're registered with SQLAlchemy.

This module ensures that all models are properly imported and available
when SQLAlchemy tries to resolve relationships.
"""

import sys
from app.core.logging import get_logger

logger = get_logger(__name__)

# Import models in dependency order - User first, then Post
try:
    from app.domains.users.models import User
    logger.info("✅ User model imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import User model: {e}")
    raise

try:
    from app.domains.posts.models import Post
    logger.info("✅ Post model imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import Post model: {e}")
    raise

# Force SQLAlchemy to configure relationships after all models are loaded


def configure_relationships():
    """Explicitly configure SQLAlchemy mappers after all models are loaded."""
    try:
        from sqlalchemy.orm import configure_mappers

        # Ensure all models are available in the registry
        from sqlalchemy import inspect
        from app.db.base import Base

        # Check if models are properly registered
        mapper_registry = Base.registry._class_registry
        logger.info(
            f"Available models in registry: {list(mapper_registry.keys())}")

        # Configure mappers
        configure_mappers()
        logger.info("✅ SQLAlchemy relationships configured successfully")
        return True
    except Exception as e:
        logger.error(f"⚠️ Error configuring SQLAlchemy relationships: {e}")
        # Don't re-raise to allow the app to continue running
        return False


# Re-export for convenience
__all__ = ["User", "Post", "configure_relationships"]
