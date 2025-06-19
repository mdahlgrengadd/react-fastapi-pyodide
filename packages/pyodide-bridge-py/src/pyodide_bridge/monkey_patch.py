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
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI must be installed to enable the monkey-patch") from exc

    if _original_fastapi_cls is not None:
        return  # already patched – idempotent

    _original_fastapi_cls = _fastapi.FastAPI  # save reference for restore/debug

    class _InterceptedFastAPI(_original_fastapi_cls):  # type: ignore[misc]
        """Drop-in replacement that auto-registers routes."""

        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self._patch_route_decorators()

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


def get_endpoints() -> List[Dict[str, Any]]:
    """Return endpoints in a frontend-friendly shape (serializable)."""
    result: List[Dict[str, Any]] = []
    for info in _registry.values():
        copy = info.copy()
        # Replace callable with its __name__ for transport
        if callable(copy.get("handler")):
            copy["handler"] = copy["handler"].__name__
        result.append(convert_to_serializable(copy))
    return result
