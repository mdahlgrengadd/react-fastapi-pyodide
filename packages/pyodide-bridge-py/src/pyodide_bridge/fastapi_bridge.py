"""
FastAPI Bridge for Pyodide environments.

This module provides a clean inheritance-based approach to extending FastAPI
for use in Pyodide environments, avoiding monkey-patching.
"""

import asyncio
import inspect
import logging
import traceback
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.routing import APIRoute
    HAS_FASTAPI = True
except ImportError:
    # Graceful fallback for environments without FastAPI
    FastAPI = object  # type: ignore
    HTTPException = Exception  # type: ignore
    APIRoute = object  # type: ignore
    HAS_FASTAPI = False

from .utils import convert_to_serializable, is_pyodide_environment

logger = logging.getLogger(__name__)

# Global registry for routes (survives app instance reloads)
_global_route_registry: Dict[str, Dict[str, Any]] = {}


class FastAPIBridge(FastAPI if HAS_FASTAPI else object):
    """
    FastAPI extension that provides clean Pyodide integration.

    Instead of monkey-patching FastAPI, this class extends it and overrides
    route decorators to capture route information for bridge execution.
    """

    def __init__(self, *args, **kwargs):
        if not HAS_FASTAPI:
            raise ImportError("FastAPI is required for PyodideBridge")

        super().__init__(*args, **kwargs)
        self._initialize_bridge()

    def _initialize_bridge(self) -> None:
        """Initialize bridge-specific functionality."""
        # Override route decorators to capture route information
        self._patch_route_methods()
        logger.info("FastAPIBridge initialized")

    def _patch_route_methods(self) -> None:
        """Override HTTP method decorators to capture route information."""
        for method in ("get", "post", "put", "patch", "delete", "options", "head"):
            original_method = getattr(super(), method)
            setattr(self, method, self._make_route_wrapper(
                original_method, method.upper()))

    def _make_route_wrapper(self, original_method: Callable, http_method: str):
        """Create a wrapper for route methods that captures route information."""
        def route_decorator(path: str, **kwargs):
            def inner(func: Callable):
                # Ensure operation_id is present
                operation_id = kwargs.get("operation_id")
                if not operation_id:
                    raise ValueError(
                        f"operation_id is required for route {http_method} {path}. "
                        f"Add operation_id='function_name' to your route decorator."
                    )

                # Register route in global registry
                self._register_route(
                    operation_id=operation_id,
                    path=path,
                    method=http_method,
                    handler=func,
                    kwargs=kwargs
                )

                # Call original FastAPI method
                return original_method(path, **kwargs)(func)
            return inner
        return route_decorator

    def _register_route(
        self,
        operation_id: str,
        path: str,
        method: str,
        handler: Callable,
        kwargs: Dict[str, Any]
    ) -> None:
        """Register route information in global registry."""
        route_info = {
            "operation_id": operation_id,
            "path": path,
            "method": method,
            "handler": handler,
            "summary": kwargs.get("summary") or handler.__doc__ or f"{method} {path}",
            "tags": kwargs.get("tags", []),
            "response_model": kwargs.get("response_model"),
            "request_model": self._extract_request_model(handler),
        }

        _global_route_registry[operation_id] = route_info
        logger.debug(f"Registered route: {operation_id} -> {method} {path}")

    def _extract_request_model(self, handler: Callable) -> Optional[str]:
        """Extract request model type from handler signature."""
        sig = inspect.signature(handler)
        for param in sig.parameters.values():
            if param.annotation != inspect.Parameter.empty:
                # Check if it's a Pydantic model or similar
                annotation = param.annotation
                if hasattr(annotation, "__name__"):
                    return annotation.__name__
        return None

    async def invoke(
        self,
        operation_id: str,
        path_params: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Invoke a registered endpoint by operation_id.

        Args:
            operation_id: The operation ID of the endpoint to invoke
            path_params: Path parameters (e.g., user_id from /users/{user_id})
            query_params: Query parameters
            body: Request body for POST/PUT/PATCH requests
            **kwargs: Additional parameters passed directly to the handler

        Returns:
            Dict containing 'content' and 'status_code'
        """
        path_params = path_params or {}
        query_params = query_params or {}

        # Find handler in registry
        route_info = _global_route_registry.get(operation_id)
        if not route_info:
            available_ops = list(_global_route_registry.keys())
            return {
                "content": {
                    "detail": f"Operation '{operation_id}' not found",
                    "available_operations": available_ops
                },
                "status_code": 404
            }

        handler = route_info["handler"]
        if not callable(handler):
            return {
                "content": {"detail": f"Handler for '{operation_id}' is not callable"},
                "status_code": 500
            }

        try:
            # Prepare handler arguments
            handler_kwargs = await self._prepare_handler_kwargs(
                handler, path_params, query_params, body, kwargs
            )

            # Execute handler
            if inspect.iscoroutinefunction(handler):
                result = await handler(**handler_kwargs)
            else:
                result = handler(**handler_kwargs)

            return {
                "content": convert_to_serializable(result),
                "status_code": 200
            }

        except HTTPException as e:
            return {
                "content": {"detail": str(e.detail)},
                "status_code": e.status_code
            }
        except Exception as e:
            logger.error(f"Error invoking {operation_id}: {e}", exc_info=True)
            return {
                "content": {
                    "detail": f"Internal server error: {str(e)}",
                    "traceback": traceback.format_exc() if is_pyodide_environment() else None
                },
                "status_code": 500
            }

    async def _prepare_handler_kwargs(
        self,
        handler: Callable,
        path_params: Dict[str, Any],
        query_params: Dict[str, Any],
        body: Any,
        extra_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare keyword arguments for handler function."""
        sig = inspect.signature(handler)
        kwargs: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            # First check extra_kwargs (direct parameters)
            if name in extra_kwargs:
                kwargs[name] = extra_kwargs[name]
            # Then check path parameters
            elif name in path_params:
                kwargs[name] = self._convert_param(
                    path_params[name], param.annotation)
            # Then check query parameters
            elif name in query_params:
                kwargs[name] = self._convert_param(
                    query_params[name], param.annotation)
            # Handle dependency injection (FastAPI Depends)
            elif hasattr(param.default, "dependency"):
                kwargs[name] = await self._resolve_dependency(param.default)
            # Handle request body (typically for POST/PUT/PATCH)
            elif body is not None and param.annotation != inspect.Parameter.empty:
                try:
                    # Try to instantiate the parameter type with the body
                    if hasattr(param.annotation, "__call__"):
                        kwargs[name] = param.annotation(
                            **body) if isinstance(body, dict) else body
                    else:
                        kwargs[name] = body
                except Exception:
                    kwargs[name] = body
            # Use default value if available
            elif param.default != inspect.Parameter.empty:
                kwargs[name] = param.default

        return kwargs

    def _convert_param(self, value: Any, annotation: Any) -> Any:
        """Convert parameter value to the expected type."""
        if annotation == inspect.Parameter.empty:
            return value

        try:
            if annotation in (int, float, bool, str):
                return annotation(value)
            return value
        except (ValueError, TypeError):
            return value

    async def _resolve_dependency(self, dependency_obj: Any) -> Any:
        """Resolve FastAPI dependency."""
        dependency = dependency_obj.dependency

        if inspect.iscoroutinefunction(dependency):
            return await dependency()
        else:
            result = dependency()
            # Handle generators (common in FastAPI dependencies)
            if hasattr(result, "__next__"):
                try:
                    return next(result)
                except StopIteration as exc:
                    return getattr(exc, "value", None)
            return result

    async def iter_chunks(
        self,
        async_generator: AsyncIterator[Any],
        max_bytes: int = 16384
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Iterate over an async generator and yield chunks with size limits.

        This ensures that individual chunks don't exceed browser limits.

        Args:
            async_generator: The async generator to iterate over
            max_bytes: Maximum bytes per chunk (default 16KB for browser compatibility)

        Yields:
            Dictionaries with 'type', 'data', and 'index' fields
        """
        index = 0
        async for item in async_generator:
            chunk_data = convert_to_serializable(item)

            # Check if chunk is too large and split if necessary
            import json
            serialized = json.dumps(chunk_data)

            if len(serialized.encode('utf-8')) > max_bytes:
                # Split large chunks
                if isinstance(chunk_data, (list, tuple)):
                    # Split lists/tuples
                    mid = len(chunk_data) // 2
                    for sub_chunk in [chunk_data[:mid], chunk_data[mid:]]:
                        yield {
                            "type": "chunk",
                            "data": sub_chunk,
                            "index": index,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        index += 1
                else:
                    # For other types, just yield as-is with warning
                    logger.warning(
                        f"Large chunk ({len(serialized)} bytes) cannot be split")
                    yield {
                        "type": "chunk",
                        "data": chunk_data,
                        "index": index,
                        "timestamp": datetime.utcnow().isoformat(),
                        "warning": "Large chunk"
                    }
                    index += 1
            else:
                yield {
                    "type": "chunk",
                    "data": chunk_data,
                    "index": index,
                    "timestamp": datetime.utcnow().isoformat()
                }
                index += 1

        # Send end marker
        yield {
            "type": "end",
            "data": None,
            "index": index,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the global route registry."""
        return _global_route_registry.copy()

    def clear_registry(self) -> None:
        """Clear the global route registry."""
        global _global_route_registry
        _global_route_registry.clear()
        logger.info("Route registry cleared")

    def get_endpoints(self) -> List[Dict[str, Any]]:
        """Get list of registered endpoints for frontend consumption."""
        endpoints = []
        for operation_id, route_info in _global_route_registry.items():
            endpoints.append({
                "operationId": operation_id,
                "path": route_info["path"],
                "method": route_info["method"],
                "summary": route_info["summary"],
                "tags": route_info["tags"],
                "responseModel": route_info.get("response_model"),
                "requestModel": route_info.get("request_model"),
            })
        return endpoints

    def get_openapi_schema(self) -> Dict[str, Any]:
        """Get OpenAPI schema including bridge-registered routes."""
        try:
            from fastapi.openapi.utils import get_openapi
            return get_openapi(
                title=getattr(self, 'title', 'FastAPI'),
                version=getattr(self, 'version', '0.1.0'),
                description=getattr(self, 'description', ''),
                routes=getattr(self, 'routes', [])
            )
        except ImportError:
            # Fallback for environments without OpenAPI utils
            return {
                "openapi": "3.0.2",
                "info": {
                    "title": getattr(self, 'title', 'FastAPI'),
                    "version": getattr(self, 'version', '0.1.0')
                },
                "paths": {}
            }
