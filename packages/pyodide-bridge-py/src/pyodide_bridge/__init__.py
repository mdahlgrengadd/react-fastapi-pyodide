"""
Pyodide Bridge for FastAPI
~~~~~~~~~~~~~~~~~~~~~~~~~

A clean, inheritance-based FastAPI bridge for Pyodide environments.

Usage:
    from pyodide_bridge import FastAPI

    app = FastAPI(title="My API")

    @app.get("/users/{user_id}", operation_id="get_user")
    async def get_user(user_id: int):
        return {"id": user_id}

    # Invoke from bridge
    result = await app.invoke("get_user", user_id=123)

    # Access original FastAPI if needed
    from pyodide_bridge import OriginalFastAPI
"""

from .fastapi_bridge import FastAPI, FastAPIBridge, OriginalFastAPI
from .utils import is_pyodide_environment, convert_to_serializable

__version__ = "0.1.0"
__all__ = ["FastAPI", "FastAPIBridge", "OriginalFastAPI",
           "is_pyodide_environment", "convert_to_serializable"]
