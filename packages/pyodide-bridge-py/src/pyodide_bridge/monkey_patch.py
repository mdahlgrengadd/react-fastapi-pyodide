"""
Opt-in monkey-patch for FastAPI that registers routes automatically.

Call `enable()` *before* importing user FastAPI code to replace
`fastapi.FastAPI` with an intercepted subclass that fills the same
global route registry used by the subclass-based bridge
(`pyodide_bridge.fastapi_bridge.FastAPI`).

Example (in Pyodide / in-browser sandbox):

    from pyodide_bridge.monkey_patch import enable
    enable(debug=1)  # enable verbose bridge debug

    # From this point plain FastAPI can be used unaltered
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    # Later, in JS ─ invoke via bridge utils
"""

from __future__ import annotations

import os
import sys
import inspect
import warnings
from typing import Any, Callable, Dict, List

# Re-use the single source-of-truth registry & helpers from the subclass bridge
try:
    from .fastapi_bridge import _global_route_registry as _registry  # type: ignore
except Exception:  # pragma: no cover – should never happen
    _registry: Dict[str, Dict[str, Any]] = {}

from .utils import convert_to_serializable  # lightweight helper

__all__ = [
    "enable",
    "get_endpoints",
]

_original_fastapi_cls: Any | None = None


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def enable(debug: int | None = None) -> None:  # noqa: D401 – imperative style
    """Patch ``fastapi.FastAPI`` globally.

    This should be called as early as possible *before* the first import of
    ``fastapi.FastAPI`` in user code. If FastAPI has already been imported it
    is still safe – the attribute will just be replaced in the existing
    module object.

    Args:
        debug: Convenience helper – if provided, sets the environment variable
            ``PYODIDE_BRIDGE_DEBUG`` to that value so that backend helpers can
            pick it up.
    """
    if debug is not None:
        os.environ["PYODIDE_BRIDGE_DEBUG"] = str(debug)

    global _original_fastapi_cls

    # Import lazily so that we do not add FastAPI to sys.modules when it is
    # genuinely unavailable (e.g. building docs).
    try:
        import fastapi as _fastapi  # type: ignore
        from fastapi.routing import APIRouter  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI must be installed to enable the monkey-patch") from exc

    if _original_fastapi_cls is not None:
        return  # already patched – idempotent

    _original_fastapi_cls = _fastapi.FastAPI  # save reference for restore/debug

    # Also patch APIRouter to ensure routes from included routers are registered
    _patch_api_router(APIRouter)

    class _InterceptedFastAPI(_original_fastapi_cls):  # type: ignore[misc]
        """Drop-in replacement that auto-registers routes."""

        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self._patch_route_decorators()

        # ----------------------------------------
        # Bridge compatibility methods
        # ----------------------------------------
        def get_endpoints(self) -> List[Dict[str, Any]]:
            """Return endpoints in a frontend-friendly shape (serializable)."""
            return get_endpoints()

        async def execute_endpoint(
            self,
            operation_id: str,
            path_params: Dict[str, Any] | None = None,
            query_params: Dict[str, Any] | None = None,
            body: Any = None
        ) -> Dict[str, Any]:
            """Execute endpoint by operation_id using the shared registry."""
            # Import the standalone function to avoid code duplication
            from .fastapi_bridge import execute_endpoint
            return await execute_endpoint(operation_id, path_params, query_params, body)

        async def invoke(
            self,
            operation_id: str,
            path_params: Dict[str, Any] | None = None,
            query_params: Dict[str, Any] | None = None,
            body: Any = None,
            **kwargs
        ) -> Dict[str, Any]:
            """Invoke endpoint by operation_id - alias for execute_endpoint for bridge compatibility."""
            return await self.execute_endpoint(operation_id, path_params, query_params, body)

        def include_router(self, router, **kwargs):
            """Override include_router to register routes from included routers."""
            # Call the original include_router first
            result = super().include_router(router, **kwargs)

            # Extract and register routes from the router
            self._extract_routes_from_router(router, **kwargs)

            return result

        def _extract_routes_from_router(self, router, prefix: str = "", **kwargs):
            """Extract routes from an APIRouter and register them."""
            router_prefix = kwargs.get("prefix", "") or getattr(
                router, "prefix", "") or ""
            full_prefix = prefix + router_prefix

            if hasattr(router, "routes"):
                for route in router.routes:
                    # Handle nested routers (Mount objects with sub-routers)
                    if hasattr(route, "app") and hasattr(route.app, "routes"):
                        # This is a nested router, recurse into it
                        nested_prefix = full_prefix + \
                            getattr(route, "path", "")
                        self._extract_routes_from_router(
                            route.app, nested_prefix, **kwargs)
                    elif hasattr(route, "methods") and hasattr(route, "endpoint"):
                        # This is a regular route
                        for method in route.methods:
                            if method in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]:
                                operation_id = getattr(
                                    route, "operation_id", None) or route.endpoint.__name__
                                full_path = full_prefix + route.path

                                _register_route(
                                    operation_id=operation_id,
                                    path=full_path,
                                    method=method,
                                    handler=route.endpoint,
                                    dec_kwargs={
                                        "summary": getattr(route, "summary", None) or route.endpoint.__doc__ or f"{method} {full_path}",
                                        "tags": kwargs.get("tags", []),
                                        "response_model": getattr(route, "response_model", None),
                                    }
                                )

        # ----------------------------------------
        # Decorator patching
        # ----------------------------------------
        def _patch_route_decorators(self) -> None:
            for _method in ("get", "post", "put", "patch", "delete", "options", "head"):
                if hasattr(self, _method):
                    original = getattr(self, _method)
                    setattr(self, _method, self._make_wrapper(
                        original, _method.upper()))

        def _make_wrapper(self, original: Callable[..., Any], http_method: str):
            def route_decorator(path: str, **dec_kwargs):  # path-level decorator
                def inner(func: Callable[..., Any]):
                    # Determine operation_id – fall back to func name if missing
                    operation_id = dec_kwargs.get(
                        "operation_id") or func.__name__

                    # Register in the shared registry (overwrite duplicates)
                    _register_route(
                        operation_id=operation_id,
                        path=path,
                        method=http_method,
                        handler=func,
                        dec_kwargs=dec_kwargs,
                    )

                    # Delegate to original decorator -> FastAPI machinery
                    return original(path, **dec_kwargs)(func)

                return inner

            return route_decorator

    # Do *the* monkey-patch
    _fastapi.FastAPI = _InterceptedFastAPI  # type: ignore[attr-defined]
    # trustworthy: same module object
    sys.modules["fastapi"].FastAPI = _InterceptedFastAPI

    # Notify – but keep it a warning to avoid noisy stdout in production
    warnings.warn(
        "pyodide-bridge monkey-patch enabled – fastapi.FastAPI has been replaced.",
        UserWarning,
        stacklevel=2,
    )


# ------------------------------------------------------------
# Registry helpers (shared with subclass bridge)
# ------------------------------------------------------------

def _register_route(*, operation_id: str, path: str, method: str, handler: Callable[..., Any], dec_kwargs: Dict[str, Any]) -> None:  # noqa: D401, E501
    """Internal: save route metadata into the shared registry."""

    _registry[operation_id] = {
        "operation_id": operation_id,
        "path": path,
        "method": method,
        "handler": handler,
        "summary": dec_kwargs.get("summary") or (handler.__doc__ or f"{method} {path}"),
        "tags": dec_kwargs.get("tags", []),
        "response_model": dec_kwargs.get("response_model"),
        # *request* model extraction is outside the scope of the patch – keep None
        "request_model": None,
    }


def _patch_api_router(APIRouter: Any) -> None:
    """Patch APIRouter methods to register routes in the global registry."""
    try:
        # Store original methods
        original_get = APIRouter.get
        original_post = APIRouter.post
        original_put = APIRouter.put
        original_patch = APIRouter.patch
        original_delete = APIRouter.delete

        def make_router_wrapper(orig_method: Callable, method: str):
            def wrapper(self, path: str, **kwargs):
                def inner(func: Callable):
                    # Determine operation_id – fall back to func name if missing
                    operation_id = kwargs.get("operation_id") or func.__name__

                    # Get router prefix if available
                    router_prefix = getattr(self, 'prefix', '') or ''
                    full_path = router_prefix + path

                    # Register in the shared registry (overwrite duplicates)
                    _register_route(
                        operation_id=operation_id,
                        path=full_path,
                        method=method,
                        handler=func,
                        dec_kwargs=kwargs,
                    )

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

    except Exception as e:
        # Don't fail the entire monkey-patch if router patching fails
        warnings.warn(f"APIRouter patching failed: {e}", UserWarning)


def get_endpoints() -> List[Dict[str, Any]]:
    """Return endpoints in a frontend-friendly shape (serializable)."""
    from .utils import extract_endpoints_from_registry
    return extract_endpoints_from_registry(_registry)
