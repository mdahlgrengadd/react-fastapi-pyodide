"""Runtime management for reactive SQLModel.

Provides global runtime that allows active-record pattern
to work without explicitly passing database sessions.

Note: Uses a simple global variable instead of ContextVar because:
1. Pyodide is single-threaded (no threading issues)
2. ContextVar doesn't work across different execution contexts in Pyodide
   (e.g., initialization vs console execution)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class Runtime:
    """Runtime configuration for reactive models.

    Attributes:
        open_session: Factory function that returns a database Session
        sync: Optional ClientSync instance (only set on client side)
    """
    open_session: Callable[[], Any]  # Returns Session
    sync: Optional[Any] = None  # ClientSync instance (client-side only)


# Global variable for current runtime (safe in single-threaded Pyodide)
# Store raw values in builtins to survive module reloads and class redefinitions
import builtins

def set_runtime(runtime: Runtime) -> None:
    """Set the current runtime.

    Args:
        runtime: Runtime configuration to use

    Example:
        >>> def open_session():
        ...     return Session(engine)
        >>> set_runtime(Runtime(open_session=open_session))
    """
    # Store as dict to survive Runtime class redefinition
    builtins.__reactive_sqlmodel_runtime__ = {
        'open_session': runtime.open_session,
        'sync': runtime.sync
    }
    print(f"[Reactive] Stored runtime in builtins: open_session={runtime.open_session}, sync={runtime.sync}")


def get_runtime() -> Runtime:
    """Get the current runtime.

    Returns:
        Current Runtime instance

    Raises:
        RuntimeError: If no runtime has been set

    Example:
        >>> runtime = get_runtime()
        >>> session = runtime.open_session()
    """
    runtime_dict = getattr(builtins, '__reactive_sqlmodel_runtime__', None)
    if runtime_dict is None:
        raise RuntimeError(
            "Reactive runtime not set. "
            "Call mount_server() or mount_client() to initialize."
        )
    # Recreate Runtime from stored values (handles class redefinition)
    return Runtime(
        open_session=runtime_dict['open_session'],
        sync=runtime_dict.get('sync')
    )
