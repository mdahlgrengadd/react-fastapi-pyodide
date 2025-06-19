"""Security utilities and dependencies."""
from typing import Dict, Any

from .runtime import get_environment_info


async def get_current_user() -> Dict[str, Any]:
    """
    Get current user for dependency injection.
    In a real app, this would validate JWT tokens, etc.
    """
    env_info = get_environment_info()

    return {
        "id": 1,
        "name": "Demo User",
        "role": "admin",
        "environment": env_info["description"],
        "database_type": env_info["type"]
    }


def get_current_user_sync() -> Dict[str, Any]:
    """Synchronous version of get_current_user for legacy compatibility."""
    env_info = get_environment_info()

    return {
        "id": 1,
        "name": "Demo User",
        "role": "admin",
        "environment": env_info["description"],
        "database_type": env_info["type"]
    }
