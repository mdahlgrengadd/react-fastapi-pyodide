"""
FastAPI Bridge for Pyodide environments.

This module provides a clean inheritance-based approach to extending FastAPI
for use in Pyodide environments, avoiding monkey-patching.

The FastAPI class in this module is a drop-in replacement for the original
FastAPI that adds Pyodide bridge functionality. The original FastAPI class
is available as OriginalFastAPI.
"""

import asyncio
import inspect
import logging
import traceback
import os
import sys
import warnings
from datetime import datetime
from types import ModuleType
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

try:
    from fastapi import FastAPI as OriginalFastAPI, HTTPException
    from fastapi.routing import APIRoute
    HAS_FASTAPI = True
except ImportError:
    # Graceful fallback for environments without FastAPI
    OriginalFastAPI = object  # type: ignore
    HTTPException = Exception  # type: ignore
    APIRoute = object  # type: ignore
    HAS_FASTAPI = False

from .utils import convert_to_serializable, is_pyodide_environment

logger = logging.getLogger(__name__)

# Global registry for routes (survives app instance reloads)
_global_route_registry: Dict[str, Dict[str, Any]] = {}

# Debug configuration
DEBUG_LEVEL = int(os.getenv("PYODIDE_BRIDGE_DEBUG", "0"))


def log(*args: Any, **kwargs: Any) -> None:
    """Log debug messages if DEBUG_LEVEL > 0."""
    if DEBUG_LEVEL > 0:
        print("[PYODIDE_BRIDGE]", *args, **kwargs)


def format_error(e: Exception, include_traceback: bool = False) -> Dict[str, Any]:
    """Format error based on debug level with size limits."""
    error_data = {
        "error": type(e).__name__,
        "detail": str(e)
    }

    if include_traceback or DEBUG_LEVEL >= 1:
        # Pre-clip stack depth before formatting to avoid WASM string limits
        tb_lines = traceback.format_exception(
            type(e), e, e.__traceback__, limit=20)
        tb_str = ''.join(tb_lines)
        # Traceback size guard: truncate to 2 KiB safely to avoid UTF-8 issues
        if len(tb_str.encode('utf-8')) > 2048:
            # Safe UTF-8 truncation to avoid breaking multibyte characters
            truncated = tb_str.encode('utf-8')[:2048].decode('utf-8', 'ignore')
            error_data["traceback"] = truncated + "..."
            error_data["traceback_truncated"] = True
        else:
            error_data["traceback"] = tb_str
            error_data["traceback_truncated"] = False

    return error_data


# ---------------------------------------------------------------------------
# Enhanced Depends shim with async support
# ---------------------------------------------------------------------------

class _DependsShim:
    __slots__ = ("dependency",)

    def __init__(self, dependency: Callable[..., Any]):
        self.dependency = dependency

    async def resolve(self) -> Any:
        """Resolve dependency, handling both sync and async functions."""
        if inspect.iscoroutinefunction(self.dependency):
            return await self.dependency()
        else:
            result = self.dependency()
            # Handle generators
            import types
            if isinstance(result, types.GeneratorType) or hasattr(result, "__next__"):
                try:
                    return next(result)
                except StopIteration as exc:
                    return exc.value
            return result

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.dependency(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Depends({self.dependency.__name__})"


class _DependsMeta(type):
    def __call__(cls, dependency: Callable[..., Any], **_kwargs: Any):
        return _DependsShim(dependency)

    def __instancecheck__(cls, instance: Any) -> bool:
        return isinstance(instance, _DependsShim)


class Depends(metaclass=_DependsMeta):
    """Public alias so user code can `from fastapi import Depends`."""


# ---------------------------------------------------------------------------
# Event-loop helper – simplified for Pyodide ≥ 0.27.7
# ---------------------------------------------------------------------------

async def _run_with_fallback(coro):
    """Run coroutine with a fallback for non-Pyodide environments.

    * In Pyodide ≥ 0.25 ``enableRunUntilComplete`` is on by default, so we can
      just ``await`` the coroutine.
    * In ordinary CPython we fall back to ``asyncio.run`` when called from a
      synchronous context.
    """
    if is_pyodide_environment():
        # Simple path – Pyodide keeps the loop alive for us
        return await coro

    # Non-Pyodide: mimic old behaviour
    try:
        asyncio.get_running_loop()
        return await coro
    except RuntimeError:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Enhanced Uvicorn stub with UserWarning and help URL
# ---------------------------------------------------------------------------

class _UvicornStub(ModuleType):
    def run(self, app: Any, host: str = "127.0.0.1", port: int = 8000, **kwargs):
        """Uvicorn stub that warns about Pyodide limitations."""
        warnings.warn(
            "Running inside Pyodide: 'uvicorn.run' is a no-op. "
            "See: https://fastapi.tiangolo.com/deployment/concepts/",
            UserWarning,
            stacklevel=2
        )
        log(f"Uvicorn stub: would run {getattr(app, 'title', 'FastAPI')} on {host}:{port}")


# Install uvicorn stub only in Pyodide environments
if is_pyodide_environment():
    sys.modules["uvicorn"] = _UvicornStub("uvicorn")


# ---------------------------------------------------------------------------
# APIRouter patching to capture routes from sub-routers
# ---------------------------------------------------------------------------

def _patch_api_router():
    """Patch APIRouter class to intercept route registrations."""
    try:
        from fastapi import APIRouter

        # Store original methods
        original_get = APIRouter.get
        original_post = APIRouter.post
        original_put = APIRouter.put
        original_patch = APIRouter.patch
        original_delete = APIRouter.delete

        def make_router_wrapper(orig_method: callable, method: str):
            def wrapper(self, path: str, **kwargs):
                def inner(func: callable):
                    log(f"Registering {method} {path} → {func.__name__} (router)")

                    # Register in our global registry with full path including prefix
                    operation_id = kwargs.get("operation_id") or func.__name__

                    # Try to get the API prefix from settings
                    full_path = path
                    try:
                        from app.core.settings import settings
                        full_path = settings.api_v1_prefix + path
                    except Exception:
                        # Fallback to default prefix if settings unavailable
                        full_path = "/api/v1" + path

                    info = {
                        "operation_id": operation_id,
                        "path": full_path,
                        "method": method,
                        "handler": func,
                        "summary": kwargs.get("summary") or func.__doc__ or f"{method} {path}",
                        "tags": kwargs.get("tags", []),
                        "response_model": kwargs.get("response_model"),
                        "request_model": None,
                    }

                    _global_route_registry[operation_id] = info
                    log(
                        f"Registered router endpoint: {operation_id} at {full_path}")

                    # Call original method
                    return orig_method(self, path, **kwargs)(func)
                return inner
            return wrapper

        # Patch router methods
        APIRouter.get = make_router_wrapper(original_get, "GET")
        APIRouter.post = make_router_wrapper(original_post, "POST")
        APIRouter.put = make_router_wrapper(original_put, "PUT")
        APIRouter.patch = make_router_wrapper(original_patch, "PATCH")
        APIRouter.delete = make_router_wrapper(original_delete, "DELETE")

        log("✅ Router class patching applied successfully")

    except Exception as e:
        log(f"❌ Router patching failed: {e}")


# Apply router patching
_patch_api_router()


# ---------------------------------------------------------------------------
# Standalone execute_endpoint function (critical for bridge compatibility)
# ---------------------------------------------------------------------------

async def execute_endpoint(
    operation_id: str,
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    body: Any = None
) -> Dict[str, Any]:
    """Execute endpoint with full async support and event-loop fallback."""
    path_params = path_params or {}
    query_params = query_params or {}

    # Handle Pyodide JsProxy conversion
    try:
        from pyodide.ffi import JsProxy, to_py
        if isinstance(body, JsProxy):
            body = body.to_py() if hasattr(body, "to_py") else to_py(body)
    except (ModuleNotFoundError, ImportError):
        if hasattr(body, "to_py"):
            try:
                body = body.to_py()
            except Exception:
                pass

    # Find handler in registry
    route_info = _global_route_registry.get(operation_id)
    if not route_info:
        available_ops = list(_global_route_registry.keys())
        error_response = {"detail": f"Handler for {operation_id} not found"}
        if DEBUG_LEVEL >= 1:
            error_response["available_endpoints"] = available_ops
        return {"content": error_response, "status_code": 404}

    handler = route_info["handler"]
    if not callable(handler):
        return {
            "content": {"detail": f"Handler for {operation_id} is not callable"},
            "status_code": 500
        }

    try:
        # Prepare arguments
        sig = inspect.signature(handler)
        kwargs = await _prepare_handler_kwargs(sig, path_params, query_params, body)

        # Execute handler with event-loop fallback
        if inspect.iscoroutinefunction(handler):
            try:
                # Try to use existing event loop - direct await to avoid double-await
                asyncio.get_running_loop()
                result = await handler(**kwargs)
            except RuntimeError:
                # No current event loop - fallback to asyncio.run
                result = await _run_with_fallback(handler(**kwargs))
        else:
            result = handler(**kwargs)

        return {
            "content": convert_to_serializable(result),
            "status_code": 200
        }

    except HTTPException as e:
        return {
            "content": format_error(e, DEBUG_LEVEL >= 1),
            "status_code": e.status_code
        }
    except Exception as e:
        log(f"Endpoint execution error: {e}")
        if DEBUG_LEVEL >= 1:
            traceback.print_exc()
        return {
            "content": format_error(e, DEBUG_LEVEL >= 1),
            "status_code": 500
        }


async def _prepare_handler_kwargs(
    sig: inspect.Signature,
    path_params: Dict[str, Any],
    query_params: Dict[str, Any],
    body: Any
) -> Dict[str, Any]:
    """Prepare handler keyword arguments with type conversion."""
    kwargs: Dict[str, Any] = {}

    def _convert_param(val: Any, annotation: Any) -> Any:
        """Convert parameter value to expected type."""
        try:
            if annotation in (int, float, bool, str):
                return annotation(val)
            return val
        except Exception:
            return val

    for name, param in sig.parameters.items():
        if name in path_params:
            kwargs[name] = _convert_param(path_params[name], param.annotation)
        elif name in query_params:
            kwargs[name] = _convert_param(query_params[name], param.annotation)
        elif isinstance(param.default, _DependsShim):
            kwargs[name] = await param.default.resolve()
        elif hasattr(param.default, "dependency"):
            # Handle FastAPI Depends
            dep = param.default.dependency
            if inspect.iscoroutinefunction(dep):
                kwargs[name] = await dep()
            else:
                result = dep()
                import types
                if isinstance(result, types.GeneratorType) or hasattr(result, "__next__"):
                    try:
                        kwargs[name] = next(result)
                    except StopIteration as exc:
                        kwargs[name] = exc.value
                else:
                    kwargs[name] = result
        elif param.default is not inspect.Parameter.empty:
            # Handle FastAPI Query, Path, etc.
            default_val = param.default

            # Check if it's a FastAPI parameter (Query, Path, etc) - check for 'default' attribute safely
            try:
                if hasattr(default_val, 'default') and not callable(default_val):
                    kwargs[name] = default_val.default
                # Check if it's a Depends object we missed
                elif isinstance(default_val, _DependsShim):
                    kwargs[name] = await default_val.resolve()
                elif hasattr(default_val, "dependency"):
                    # Handle FastAPI Depends that we might have missed
                    dep = default_val.dependency
                    if inspect.iscoroutinefunction(dep):
                        kwargs[name] = await dep()
                    else:
                        result = dep()
                        import types
                        if isinstance(result, types.GeneratorType) or hasattr(result, "__next__"):
                            try:
                                kwargs[name] = next(result)
                            except StopIteration as exc:
                                kwargs[name] = exc.value
                        else:
                            kwargs[name] = result
                else:
                    kwargs[name] = default_val
            except Exception as e:
                log(f"Error processing param {name}: {e}")
                kwargs[name] = None
        elif body is not None and param.annotation != inspect._empty:
            # Try to instantiate Pydantic model
            try:
                kwargs[name] = param.annotation(**body)
            except Exception:
                kwargs[name] = body

    return kwargs


class FastAPI(OriginalFastAPI if HAS_FASTAPI else object):
    """
    FastAPI extension that provides clean Pyodide integration.

    This is a drop-in replacement for the original FastAPI that extends it
    and overrides route decorators to capture route information for bridge execution.    The original FastAPI class is available as OriginalFastAPI if needed.
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
        # Add bridge-specific endpoints
        self._add_bridge_endpoints()
        logger.info("FastAPI (with Pyodide bridge) initialized")

    def _patch_route_methods(self) -> None:
        """Override HTTP method decorators to capture route information."""
        for method in ("get", "post", "put", "patch", "delete", "options", "head"):
            original_method = getattr(super(), method)
            setattr(self, method, self._make_route_wrapper(
                original_method, method.upper()))

        # Also override include_router to capture routes from sub-routers
        self._original_include_router = super().include_router

    def _add_bridge_endpoints(self) -> None:
        """Add bridge-specific endpoints for introspection and invocation."""

        @self.get("/bridge/endpoints",
                  operation_id="get_bridge_endpoints",
                  summary="Get bridge endpoints",
                  tags=["bridge"])
        async def get_bridge_endpoints():
            """Get list of registered bridge endpoints."""
            return self.get_endpoints()

        @self.get("/bridge/registry",
                  operation_id="get_bridge_registry",
                  summary="Get bridge registry",
                  tags=["bridge"])
        async def get_bridge_registry():
            """Get the internal bridge registry for debugging."""
            return self.get_registry()

        @self.post("/bridge/invoke/{operation_id}",
                   operation_id="invoke_bridge_endpoint",
                   summary="Invoke endpoint via bridge",
                   tags=["bridge"])
        async def invoke_bridge_endpoint(
            operation_id: str,
            path_params: Dict[str, Any] = None,
            query_params: Dict[str, Any] = None,
            body: Any = None
        ):
            """Invoke any registered endpoint via the bridge."""
            return await self.invoke(
                operation_id=operation_id,
                path_params=path_params or {},
                query_params=query_params or {},
                body=body
            )

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

    def _include_router_wrapper(self, router, **kwargs):
        """Wrapper for include_router that captures routes from the included router."""
        # First include the router normally
        result = self._original_include_router(router, **kwargs)

        # Then extract and register routes from the included router
        self._extract_routes_from_router(router, **kwargs)

        return result

    def include_router(self, router, **kwargs):
        """Override include_router to capture routes from included routers."""
        return self._include_router_wrapper(router, **kwargs)

    def _extract_routes_from_router(self, router, prefix: str = "", **kwargs):
        """Extract and register routes from an APIRouter."""
        try:
            from fastapi.routing import APIRoute

            # Get the prefix for this router inclusion
            router_prefix = kwargs.get("prefix", prefix or "")

            # Iterate through routes in the router
            for route in router.routes:
                if isinstance(route, APIRoute):
                    # Extract route information
                    for method in route.methods:
                        if method.lower() in ("get", "post", "put", "patch", "delete", "options", "head"):
                            # Get operation_id from the route
                            operation_id = getattr(route, 'operation_id', None)

                            if operation_id:
                                # Construct full path
                                full_path = router_prefix + route.path

                                # Register the route
                                self._register_route(
                                    operation_id=operation_id,
                                    path=full_path,
                                    method=method.upper(),
                                    handler=route.endpoint,
                                    kwargs={}
                                )

                                logger.debug(
                                    f"Captured route from router: {operation_id} -> {method.upper()} {full_path}")

        except Exception as e:
            logger.warning(f"Error extracting routes from router: {e}")

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
                    # Use default value if available
                    kwargs[name] = body
            elif param.default != inspect.Parameter.empty:
                # Handle FastAPI Query parameters specially
                if hasattr(param.default, 'default'):
                    # It's a FastAPI Query, Path, Body, etc. - use its default value
                    kwargs[name] = param.default.default
                else:
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
        # Filter out bridge meta-endpoints that shouldn't be directly callable from UI
        excluded_operations = {
            "get_bridge_endpoints",
            "get_bridge_registry",
            "invoke_bridge_endpoint"
        }

        for operation_id, route_info in _global_route_registry.items():
            if operation_id not in excluded_operations:
                # Safely serialize each field
                endpoint_data = {
                    "operationId": operation_id,
                    "path": route_info["path"],
                    "method": route_info["method"],
                    "summary": route_info["summary"],
                    "tags": route_info.get("tags", []),
                }

                # Safely handle response_model
                response_model = route_info.get("response_model")
                if response_model:
                    endpoint_data["responseModel"] = convert_to_serializable(
                        response_model)
                else:
                    endpoint_data["responseModel"] = None

                # Safely handle request_model
                request_model = route_info.get("request_model")
                if request_model:
                    endpoint_data["requestModel"] = convert_to_serializable(
                        request_model)
                else:
                    endpoint_data["requestModel"] = None

                endpoints.append(endpoint_data)

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
                },                "paths": {}
            }


# ---------------------------------------------------------------------------
# Standalone functions for direct JavaScript access
# ---------------------------------------------------------------------------

def get_endpoints() -> List[Dict[str, Any]]:
    """Get list of registered endpoints (standalone function for JS access)."""
    endpoints = []
    # Filter out bridge meta-endpoints that shouldn't be directly callable from UI
    excluded_operations = {
        "get_bridge_endpoints",
        "get_bridge_registry",
        "invoke_bridge_endpoint"
    }

    for operation_id, route_info in _global_route_registry.items():
        if operation_id not in excluded_operations:
            # Use only basic, safe data types
            endpoint_data = {
                "operationId": str(operation_id),
                "path": str(route_info.get("path", "")),
                "method": str(route_info.get("method", "")),
                "summary": str(route_info.get("summary", "")),
                # Ensure it's a plain list
                "tags": list(route_info.get("tags", [])),
                "responseModel": None,  # Skip complex models for now
                "requestModel": None,   # Skip complex models for now
            }

            # Safely handle handler (convert to name for serialization)
            handler = route_info.get("handler")
            if callable(handler):
                endpoint_data["handler"] = str(handler.__name__)
            else:
                endpoint_data["handler"] = "unknown"

            endpoints.append(endpoint_data)

    return endpoints


def get_endpoints_ultra_safe() -> List[Dict[str, Any]]:
    """Ultra-safe endpoint extraction that avoids all complex objects."""
    try:
        endpoints = []
        registry_keys = list(_global_route_registry.keys())

        for operation_id in registry_keys:
            if operation_id in {"get_bridge_endpoints", "get_bridge_registry", "invoke_bridge_endpoint"}:
                continue

            route_info = _global_route_registry.get(operation_id, {})

            # Extract only string/basic values, no complex objects
            endpoint = {
                "operationId": str(operation_id),
                "path": str(route_info.get("path", "/")),
                "method": str(route_info.get("method", "GET")),
                "summary": str(route_info.get("summary", "")),
                "tags": [],  # Empty list to avoid any serialization issues
                "handler": "unknown"
            }

            # Try to get handler name safely
            try:
                handler = route_info.get("handler")
                if handler and hasattr(handler, "__name__"):
                    endpoint["handler"] = str(handler.__name__)
            except Exception:
                pass  # Keep default "unknown"

            endpoints.append(endpoint)

        return endpoints
    except Exception as e:
        log(f"Error in ultra-safe endpoint extraction: {e}")
        return []


def get_openapi_schema() -> Dict[str, Any]:
    """Generate OpenAPI schema (standalone function for JS access)."""
    try:
        from fastapi.openapi.utils import get_openapi
        # This would need a FastAPI app instance - simplified for compatibility
        return {
            "openapi": "3.0.2",
            "info": {"title": "FastAPI", "version": "0.1.0"},
            "paths": {}
        }
    except ImportError:
        return {
            "openapi": "3.0.2",
            "info": {"title": "FastAPI", "version": "0.1.0"},
            "paths": {}
        }


# Backwards compatibility alias
FastAPIBridge = FastAPI
