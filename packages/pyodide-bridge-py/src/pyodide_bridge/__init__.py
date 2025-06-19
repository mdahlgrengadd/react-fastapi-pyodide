"""
Pyodide Bridge for FastAPI
~~~~~~~~~~~~~~~~~~~~~~~~~

A clean, inheritance-based FastAPI bridge for Pyodide environments.

Usage:
    from pyodide_bridge import FastAPIBridge

    app = FastAPIBridge(title="My API")

    @app.get("/users/{user_id}", operation_id="get_user")
    async def get_user(user_id: int):
        return {"id": user_id}

    # Invoke from bridge
    result = await app.invoke("get_user", user_id=123)
"""

from .fastapi_bridge import FastAPIBridge
from .utils import is_pyodide_environment, convert_to_serializable

__version__ = "0.1.0"
__all__ = ["FastAPIBridge", "is_pyodide_environment",
           "convert_to_serializable"]
