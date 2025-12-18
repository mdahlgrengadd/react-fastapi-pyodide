"""Runtime detection for Pyodide vs CPython environments."""
import sys
import os
from typing import Literal


def is_pyodide() -> bool:
    """Check if running in Pyodide environment."""
    # Multiple checks to ensure correct detection
    return (
        "pyodide" in sys.modules or
        hasattr(sys, "_emscripten_info") or
        sys.platform == "emscripten" or
        "emscripten" in sys.platform.lower()
    )


# Environment detection - use function for accurate runtime check
IS_PYODIDE = is_pyodide()

# Environment type
ENV_TYPE = Literal["pyodide-persistent",
                   "fastapi-production", "fastapi-development"]


def get_environment() -> ENV_TYPE:
    """Get the current runtime environment."""
    if is_pyodide():
        return "pyodide-persistent"
    elif os.getenv("DATABASE_URL"):
        return "fastapi-production"
    else:
        return "fastapi-development"


def get_environment_info() -> dict:
    """Get comprehensive environment information."""
    env = get_environment()
    pyodide_detected = is_pyodide()

    environment_descriptions = {
        "pyodide-persistent": "Pyodide Browser (Persistent)",
        "fastapi-production": "FastAPI Backend (Production)",
        "fastapi-development": "FastAPI Backend (Development)"
    }

    return {
        "type": env,
        "description": environment_descriptions[env],
        "is_pyodide": pyodide_detected,
        "has_database_url": bool(os.getenv("DATABASE_URL")),
        "python_version": sys.version,
        "platform": sys.platform if not pyodide_detected else "pyodide"
    }
