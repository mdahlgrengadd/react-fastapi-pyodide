# bridge_final.py – Production-ready, Pyodide-optimized FastAPI bridge
# -----------------------------------------------------------------------------------
#  • Early monkey-patch to prevent import-order races
#  • Event-loop fallback for Pyodide compatibility
#  • Async endpoint and dependency support with proper error handling
#  • Accurate SQLAlchemy detection with DeclarativeMeta
#  • Safer serialization with orjson options and bounded _seen handling
#  • Structured debug traces with size limits (0=compact, 1=full+truncated)
#  • Deduplicated endpoint registry with direct callable references
#  • Uvicorn stub with proper UserWarning and help URL
#  • Lazy app proxy to handle early imports
# -----------------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import os
import sys
import traceback
import warnings
from datetime import date, datetime
from decimal import Decimal
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional

__version__ = "0.3.0"

# Import FastAPI and related modules early
try:
    from fastapi import FastAPI as OriginalFastAPI, HTTPException
    from fastapi.encoders import jsonable_encoder
    from fastapi.openapi.utils import get_openapi
except ImportError:
    # Handle case where FastAPI isn't available
    OriginalFastAPI = object  # type: ignore
    HTTPException = Exception  # type: ignore
    def jsonable_encoder(x): return x  # type: ignore
    get_openapi = lambda **kwargs: {}  # type: ignore

try:
    from sqlalchemy.orm import DeclarativeMeta
    # Also import newer registry-based approach for SQLAlchemy 2.x
    try:
        from sqlalchemy.orm import registry
        HAS_SQLALCHEMY_REGISTRY = True
    except ImportError:
        HAS_SQLALCHEMY_REGISTRY = False
except ImportError:
    DeclarativeMeta = type  # type: ignore
    HAS_SQLALCHEMY_REGISTRY = False

# Optional orjson for faster serialization
try:
    import orjson
    HAS_ORJSON = True
    ORJSON_OPTIONS = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_PASSTHROUGH_DATACLASS
except ImportError:
    HAS_ORJSON = False
    ORJSON_OPTIONS = 0

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_original_fastapi_class = None
_app: Optional[Any] = None
_endpoints_registry: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Debug configuration with structured levels
# ---------------------------------------------------------------------------

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
# FastAPI interception class (must be defined before monkey-patch)
# ---------------------------------------------------------------------------


class _InterceptedFastAPI(OriginalFastAPI if OriginalFastAPI != object else object):
    def __new__(cls, *args: Any, **kwargs: Any):
        global _app
        if _app is None:
            log("Creating FastAPI singleton instance")
            if OriginalFastAPI != object:
                _app = super().__new__(cls)
                super(_InterceptedFastAPI, _app).__init__(*args, **kwargs)
                _patch_route_decorators(_app)
            else:
                # Fallback when FastAPI not available
                _app = object.__new__(cls)
                _app.title = kwargs.get('title', 'FastAPI')
                _app.version = kwargs.get('version', '0.1.0')
                _app.description = kwargs.get('description', '')
                _app.routes = []
        else:
            # Update metadata on subsequent calls
            metadata_changed = False
            for attr in ("title", "version", "description", "openapi_tags"):
                if attr in kwargs and hasattr(_app, attr):
                    setattr(_app, attr, kwargs[attr])
                    metadata_changed = True

            # Clear cached OpenAPI schema when metadata changes
            if metadata_changed and hasattr(_app, "openapi_schema"):
                _app.openapi_schema = None
        return _app

# ---------------------------------------------------------------------------
# EARLY MONKEY-PATCH: Must happen before any third-party imports
# ---------------------------------------------------------------------------


def _apply_early_monkey_patch():
    """Apply FastAPI monkey-patch before any third-party code can import it."""
    global _original_fastapi_class

    if _original_fastapi_class is not None:
        return  # Already patched

    try:
        _original_fastapi_class = OriginalFastAPI

        # Apply the monkey-patch immediately
        import fastapi as _fastapi_module
        _fastapi_module.FastAPI = _InterceptedFastAPI
        sys.modules["fastapi"].FastAPI = _InterceptedFastAPI

        log("Early monkey-patch applied successfully")
    except Exception as e:
        log(f"Monkey-patch failed: {e}")


# Apply early patch
_apply_early_monkey_patch()

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
# Enhanced serialization with orjson support and proper _seen handling
# ---------------------------------------------------------------------------


def _is_sqlalchemy_model(obj: Any) -> bool:
    """Accurate SQLAlchemy model detection using DeclarativeMeta and registry approach."""
    try:
        # Primary check: DeclarativeMeta (works for both SQLAlchemy 1.x and 2.x)
        if isinstance(obj.__class__, DeclarativeMeta):
            return True

        # Additional check for newer registry-based approach (SQLAlchemy 2.x)
        if HAS_SQLALCHEMY_REGISTRY:
            # Check if object has SQLAlchemy registry metadata
            if hasattr(obj, '__table__') and hasattr(obj, '__mapper__'):
                return True

        return False
    except (AttributeError, TypeError):
        return False


def convert_to_serializable(obj: Any, _seen: Optional[set[int]] = None) -> Any:
    """Enhanced serialization with bounded circular reference handling."""
    # Always use a fresh set per call to avoid shared state between concurrent requests
    if _seen is None:
        _seen = set()

    oid = id(obj)
    if oid in _seen:
        return "<circular>"

    # Add to seen set with try/finally for memory control
    _seen.add(oid)
    try:
        # Primitives first
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)

        # Collections
        if isinstance(obj, dict):
            return {k: convert_to_serializable(v, _seen) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [convert_to_serializable(v, _seen) for v in obj]

        # Pydantic BaseModel (v2 preferred, v1 fallback)
        if hasattr(obj, "model_dump"):
            try:
                if hasattr(obj, "model_dump_json") and HAS_ORJSON:
                    return orjson.loads(obj.model_dump_json())
                return convert_to_serializable(obj.model_dump(), _seen)
            except Exception:
                pass
        if hasattr(obj, "dict"):
            try:
                return convert_to_serializable(obj.dict(), _seen)
            except Exception:
                pass

        # SQLAlchemy model with accurate detection
        if _is_sqlalchemy_model(obj):
            data: Dict[str, Any] = {}
            try:
                for col in getattr(obj, "__table__").columns:
                    data[col.name] = convert_to_serializable(
                        getattr(obj, col.name, None), _seen)
                # Add relationships from __dict__
                for k, v in obj.__dict__.items():
                    if not k.startswith("_") and k not in data:
                        data[k] = convert_to_serializable(v, _seen)
                return data
            except Exception as e:
                log(f"SQLAlchemy serialization error: {e}")
                return str(obj)

        # Fallback with orjson support and options
        try:
            if HAS_ORJSON:
                return orjson.loads(orjson.dumps(obj, default=str, option=ORJSON_OPTIONS))
            return jsonable_encoder(obj)
        except Exception:
            return str(obj)
    finally:
        # Remove from seen set to bound memory growth
        _seen.discard(oid)

# ---------------------------------------------------------------------------
# Route decorator patching with async support
# ---------------------------------------------------------------------------


def _patch_route_decorators(app: Any) -> None:
    """Patch HTTP method decorators to support async handlers."""
    def make_wrapper(orig: Callable[..., Any], method: str):
        def decorator(path: str, **kwargs):
            def inner(func: Callable[..., Any]):
                log(f"Registering {method} {path} → {func.__name__}")
                wrapped = _make_dependency_wrapper(func)
                _register_endpoint(path, method, func, kwargs)
                return orig(path, **kwargs)(wrapped)
            return inner
        return decorator

    for method in ("get", "post", "put", "patch", "delete"):
        if hasattr(app, method):
            setattr(app, method, make_wrapper(
                getattr(app, method), method.upper()))

# ---------------------------------------------------------------------------
# Enhanced dependency wrapper with async support and event-loop fallback
# ---------------------------------------------------------------------------


def _make_dependency_wrapper(func: Callable[..., Any]):
    """Wrap function to handle dependencies and async execution."""
    sig = inspect.signature(func)
    is_async = inspect.iscoroutinefunction(func)

    if is_async:
        async def async_wrapper(**request_kwargs):
            resolved = await _resolve_dependencies(sig, request_kwargs, is_sync_context=False)
            return await func(**resolved)

        functools.update_wrapper(async_wrapper, func)
        async_wrapper.__signature__ = sig  # type: ignore
        return async_wrapper
    else:
        def sync_wrapper(**request_kwargs):
            # Handle dependencies synchronously - check for async deps
            resolved = _resolve_dependencies_sync(sig, request_kwargs)
            result = func(**resolved)
            return convert_to_serializable(result)

        functools.update_wrapper(sync_wrapper, func)
        sync_wrapper.__signature__ = sig  # type: ignore
        return sync_wrapper


def _resolve_dependencies_sync(sig: inspect.Signature, request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve dependencies synchronously, raising error for async deps."""
    resolved: Dict[str, Any] = {}

    for name, param in sig.parameters.items():
        default = param.default

        if isinstance(default, _DependsShim):
            # Check for async dependency in sync context
            if inspect.iscoroutinefunction(default.dependency):
                raise HTTPException(
                    500, f"Cannot use async dependency '{name}' in sync handler")
            else:
                try:
                    result = default.dependency()
                    if hasattr(result, '__next__'):  # Generator
                        try:
                            resolved[name] = next(result)
                        except StopIteration as exc:
                            resolved[name] = exc.value
                    else:
                        resolved[name] = result
                except Exception as e:
                    log(f"Error resolving dependency {name}: {e}")
                    resolved[name] = None
        elif name in request_kwargs:
            resolved[name] = request_kwargs[name]
        elif param.default is not inspect.Parameter.empty:
            # Handle FastAPI Query, Path, etc parameters
            if hasattr(param.default, 'default'):
                resolved[name] = param.default.default
            else:
                resolved[name] = param.default
        else:
            resolved[name] = None

    return resolved


async def _resolve_dependencies(sig: inspect.Signature, request_kwargs: Dict[str, Any], is_sync_context: bool = False) -> Dict[str, Any]:
    """Resolve function dependencies, handling both sync and async."""
    resolved: Dict[str, Any] = {}

    for name, param in sig.parameters.items():
        default = param.default

        if isinstance(default, _DependsShim):
            resolved[name] = await default.resolve()
        elif hasattr(default, "dependency"):
            # Handle original FastAPI Depends
            dep = default.dependency
            if inspect.iscoroutinefunction(dep):
                resolved[name] = await dep()
            else:
                result = dep()
                # Handle generators
                import types
                if isinstance(result, types.GeneratorType) or hasattr(result, "__next__"):
                    try:
                        resolved[name] = next(result)
                    except StopIteration as exc:
                        resolved[name] = exc.value
                else:
                    resolved[name] = result
        elif name in request_kwargs:
            resolved[name] = request_kwargs[name]
        elif hasattr(default, "default"):
            resolved[name] = default.default
        else:
            resolved[name] = default if default is not inspect.Parameter.empty else None

    return resolved

# ---------------------------------------------------------------------------
# Deduplicated endpoint registry with direct callable references
# ---------------------------------------------------------------------------


def _register_endpoint(path: str, method: str, func: Callable[..., Any], decorator_kwargs: Dict[str, Any]):
    """Register endpoint in deduplicated registry with direct callable reference."""
    operation_id = decorator_kwargs.get("operation_id") or func.__name__

    info = {
        "path": path,
        "method": method,
        "operationId": operation_id,
        "summary": decorator_kwargs.get("summary") or func.__doc__ or f"{method} {path}",
        "handler": func,  # Store direct callable instead of name
    }

    # Overwrite if already exists (deduplication)
    _endpoints_registry[operation_id] = info
    log(f"Registered endpoint: {operation_id}")

# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------


def get_endpoints() -> List[Dict[str, Any]]:
    """Return list of registered endpoints."""
    # First try to get from registry (for endpoints registered through our decorators)
    result = []
    for endpoint in _endpoints_registry.values():
        endpoint_copy = endpoint.copy()
        if callable(endpoint_copy["handler"]):
            endpoint_copy["handler"] = endpoint_copy["handler"].__name__
        result.append(endpoint_copy)

    # If registry is empty, read directly from FastAPI app routes
    if not result and _app is not None and hasattr(_app, 'routes'):
        for route in _app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                # This is a regular route (not WebSocket, etc.)
                for method in route.methods:
                    if method.upper() not in ('HEAD', 'OPTIONS'):  # Skip auto-generated methods
                        # Generate operation ID properly
                        path_normalized = route.path.replace(
                            '/', '_').replace('{', '').replace('}', '')
                        if path_normalized.startswith('_'):
                            # Remove leading underscore only
                            path_normalized = path_normalized[1:]
                        endpoint_id = f"{method.upper()}__{path_normalized}"

                        endpoint_info = {
                            'operationId': endpoint_id,
                            'method': method.upper(),
                            'path': route.path,
                            'summary': getattr(route.endpoint, '__doc__', '') or f"{method.upper()} {route.path}",
                            'handler': route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else 'unknown'
                        }
                        result.append(endpoint_info)

    return result


def get_openapi_schema() -> Dict[str, Any]:
    """Generate OpenAPI schema."""
    if _app is None:
        raise RuntimeError("FastAPI app not initialized yet")

    if hasattr(_app, 'routes'):
        return get_openapi(
            title=getattr(_app, 'title', 'FastAPI'),
            version=getattr(_app, 'version', '0.1.0'),
            description=getattr(_app, 'description', ''),
            routes=_app.routes
        )
    return {}

# ---------------------------------------------------------------------------
# Enhanced execute_endpoint with full async support and event-loop fallback
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
                pass    # Find handler - first check registry, then check FastAPI routes
    handler = None

    if operation_id in _endpoints_registry:
        handler = _endpoints_registry[operation_id]["handler"]
    elif _app is not None and hasattr(_app, 'routes'):
        # Look for the endpoint in FastAPI routes
        for route in _app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    if method.upper() not in ('HEAD', 'OPTIONS'):
                        # Generate operation ID the same way as in get_endpoints
                        path_normalized = route.path.replace(
                            '/', '_').replace('{', '').replace('}', '')
                        if path_normalized.startswith('_'):
                            path_normalized = path_normalized[1:]
                        endpoint_id = f"{method.upper()}__{path_normalized}"

                        if endpoint_id == operation_id:
                            handler = route.endpoint
                            break
                if handler:
                    break

    if not handler:
        available_endpoints = list(_endpoints_registry.keys())
        # Also add endpoints from FastAPI routes if registry is empty
        if not available_endpoints and _app is not None and hasattr(_app, 'routes'):
            for route in _app.routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    for method in route.methods:
                        if method.upper() not in ('HEAD', 'OPTIONS'):
                            path_normalized = route.path.replace(
                                '/', '_').replace('{', '').replace('}', '')
                            if path_normalized.startswith('_'):
                                path_normalized = path_normalized[1:]
                            endpoint_id = f"{method.upper()}__{path_normalized}"
                            available_endpoints.append(endpoint_id)

        error_response = {"detail": f"Handler for {operation_id} not found"}
        if DEBUG_LEVEL >= 1:
            error_response["available_endpoints"] = available_endpoints
        return {"content": error_response, "status_code": 404}

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


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------


try:
    import pyodide  # type: ignore
    IS_PYODIDE = True
except ImportError:
    IS_PYODIDE = False


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

    if IS_PYODIDE:
        # Simple path – Pyodide keeps the loop alive for us
        return await coro

    # Non-Pyodide: mimic old behaviour
    try:
        asyncio.get_running_loop()
        return await coro
    except RuntimeError:
        return asyncio.run(coro)


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


# Install uvicorn stub
sys.modules["uvicorn"] = _UvicornStub("uvicorn")

# ---------------------------------------------------------------------------
# Endpoint registry and execution
# ---------------------------------------------------------------------------

# Global endpoint registry
_endpoints_registry = {}


# ---------------------------------------------------------------------------
# Lazy app proxy to handle early imports
# ---------------------------------------------------------------------------


class _AppProxy:
    """Lazy proxy for FastAPI app that raises if accessed before initialization."""

    def __getattr__(self, item):
        if _app is None:
            raise RuntimeError("FastAPI() not yet called")
        return getattr(_app, item)


app = _AppProxy()

# ---------------------------------------------------------------------------
# Legacy compatibility
# ---------------------------------------------------------------------------


class EnhancedFastAPIBridge:
    """Legacy compatibility shim for existing code."""

    def __init__(self):
        pass

    @property
    def app(self):
        return _app

    def get_endpoints(self):
        return get_endpoints()

    def get_openapi_schema(self):
        return get_openapi_schema()


# Default instance for existing import patterns
bridge = EnhancedFastAPIBridge()

# Public API
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
