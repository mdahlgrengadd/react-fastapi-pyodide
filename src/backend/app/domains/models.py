"""
Import all domain models to ensure they're registered with SQLModel.

This module ensures that all models are properly imported and available
when the application starts.
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


def configure_relationships():
    """Configure model relationships.

    SQLModel handles relationship configuration automatically through its
    integration with SQLAlchemy. This function is kept for backwards
    compatibility with existing code that calls it.

    Note: Relationships are currently commented out in the models since
    we're focusing on reactive sync first. They can be re-enabled later.
    """
    logger.info("✅ SQLModel relationships configured (automatic)")
    return True


# Re-export for convenience
__all__ = ["User", "Post", "configure_relationships"]
