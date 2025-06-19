# Compatibility shim for apps/backend/src/app/core/bridge.py
#
# This file now imports everything from the pyodide-bridge-py package
# to maintain backward compatibility while consolidating functionality.

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

# Enable monkey-patch by default to maintain existing behavior
try:
    from pyodide_bridge import enable_monkey_patch
    enable_monkey_patch()
except ImportError:
    warnings.warn(
        "pyodide-bridge package not found - bridge functionality disabled")

# Import all the functionality from the package
try:
    from pyodide_bridge import (
        FastAPI as _FastAPI,
        execute_endpoint,
        Depends,
        convert_to_serializable,
        is_pyodide_environment,
    )
    from pyodide_bridge.fastapi_bridge import (
        _global_route_registry as _endpoints_registry,
        log,
        format_error,
    )

    # For backward compatibility, expose the same interface
    def get_endpoints() -> List[Dict[str, Any]]:
        """Return list of registered endpoints."""
        result = []
        for endpoint in _endpoints_registry.values():
            endpoint_copy = endpoint.copy()
            if callable(endpoint_copy.get("handler")):
                endpoint_copy["handler"] = endpoint_copy["handler"].__name__
            # Convert to the expected format
            endpoint_copy["operationId"] = endpoint_copy.pop(
                "operation_id", endpoint_copy.get("operationId"))
            result.append(endpoint_copy)
        return result

    def get_openapi_schema() -> Dict[str, Any]:
        """Generate OpenAPI schema."""
        # This would need a FastAPI app instance - simplified for compatibility
        return {
            "openapi": "3.0.2",
            "info": {"title": "FastAPI", "version": "0.1.0"},
            "paths": {}
        }

    # Legacy compatibility classes
    class EnhancedFastAPIBridge:
        """Legacy compatibility shim for existing code."""

        def __init__(self):
            pass

        @property
        def app(self):
            # Return None since we don't have a singleton app in the package approach
            return None

        def get_endpoints(self):
            return get_endpoints()

        def get_openapi_schema(self):
            return get_openapi_schema()

    # Default instance for existing import patterns
    bridge = EnhancedFastAPIBridge()

    # App proxy - simplified since package doesn't use singleton pattern
    class _AppProxy:
        """Lazy proxy for FastAPI app that raises if accessed before initialization."""

        def __getattr__(self, item):
            raise RuntimeError(
                "App proxy not supported in package-based bridge - use FastAPI() directly")

    app = _AppProxy()

    __version__ = "0.3.0"

    # Public API for backward compatibility
    __all__ = [
        "Depends",
        "convert_to_serializable",
        "execute_endpoint",
        "get_endpoints",
        "get_openapi_schema",
        "app",
        "bridge",
        "EnhancedFastAPIBridge",
        "__version__",
    ]

except ImportError as e:
    warnings.warn(f"Failed to import from pyodide-bridge package: {e}")

    # Minimal fallback implementations
    def get_endpoints():
        return []

    def get_openapi_schema():
        return {}

    async def execute_endpoint(*args, **kwargs):
        return {"content": {"detail": "Bridge not available"}, "status_code": 500}

    class Depends:
        pass

    def convert_to_serializable(obj):
        return str(obj)

    class EnhancedFastAPIBridge:
        def get_endpoints(self):
            return []

        def get_openapi_schema(self):
            return {}

    bridge = EnhancedFastAPIBridge()
    app = None
    __version__ = "0.3.0"
