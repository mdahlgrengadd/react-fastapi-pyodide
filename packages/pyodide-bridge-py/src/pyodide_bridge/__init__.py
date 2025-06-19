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

from .fastapi_bridge import FastAPI, FastAPIBridge, OriginalFastAPI, execute_endpoint, Depends, get_endpoints, get_openapi_schema, get_endpoints_ultra_safe
from .utils import is_pyodide_environment, convert_to_serializable, extract_endpoints_from_registry, extract_endpoints_ultra_safe
from .monkey_patch import enable as enable_monkey_patch

__version__ = "0.1.0"
__all__ = ["FastAPI", "FastAPIBridge", "OriginalFastAPI",
           "is_pyodide_environment", "convert_to_serializable",
           "enable_monkey_patch", "execute_endpoint", "Depends",
           "get_endpoints", "get_openapi_schema", "get_endpoints_ultra_safe",
           "extract_endpoints_from_registry", "extract_endpoints_ultra_safe"]
