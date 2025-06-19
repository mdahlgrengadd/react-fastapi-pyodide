"""Runtime detection for Pyodide vs CPython environments."""
import sys
import os
from typing import Literal

# Environment detection
IS_PYODIDE = "pyodide" in sys.modules

# Environment type
ENV_TYPE = Literal["pyodide-persistent",
                   "fastapi-production", "fastapi-development"]


def get_environment() -> ENV_TYPE:
    """Get the current runtime environment."""
    if IS_PYODIDE:
        return "pyodide-persistent"
    elif os.getenv("DATABASE_URL"):
        return "fastapi-production"
    else:
        return "fastapi-development"


def get_environment_info() -> dict:
    """Get comprehensive environment information."""
    env = get_environment()

    environment_descriptions = {
        "pyodide-persistent": "Pyodide Browser (Persistent)",
        "fastapi-production": "FastAPI Backend (Production)",
        "fastapi-development": "FastAPI Backend (Development)"
    }

    return {
        "type": env,
        "description": environment_descriptions[env],
        "is_pyodide": IS_PYODIDE,
        "has_database_url": bool(os.getenv("DATABASE_URL")),
        "python_version": sys.version,
        "platform": sys.platform if not IS_PYODIDE else "pyodide"
    }
