"""
Utility functions for Pyodide Bridge.

Contains helper functions for environment detection, serialization,
and other common bridge operations.
"""

import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Set

# Check if we're running in Pyodide
try:
    import pyodide  # type: ignore
    IS_PYODIDE = True
except ImportError:
    IS_PYODIDE = False

# Check for SQLAlchemy
try:
    from sqlalchemy.orm import DeclarativeMeta
    try:
        from sqlalchemy.orm import registry
        HAS_SQLALCHEMY_REGISTRY = True
    except ImportError:
        HAS_SQLALCHEMY_REGISTRY = False
    HAS_SQLALCHEMY = True
except ImportError:
    DeclarativeMeta = type  # type: ignore
    HAS_SQLALCHEMY_REGISTRY = False
    HAS_SQLALCHEMY = False

# Check for orjson (faster JSON serialization)
try:
    import orjson
    HAS_ORJSON = True
    ORJSON_OPTIONS = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_PASSTHROUGH_DATACLASS
except ImportError:
    HAS_ORJSON = False
    ORJSON_OPTIONS = 0


def is_pyodide_environment() -> bool:
    """Check if we're running in a Pyodide environment."""
    return IS_PYODIDE


def is_sqlalchemy_model(obj: Any) -> bool:
    """
    Check if an object is a SQLAlchemy model.

    Uses accurate detection for both SQLAlchemy 1.x and 2.x.
    """
    if not HAS_SQLALCHEMY:
        return False

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


def convert_to_serializable(obj: Any, _seen: Optional[Set[int]] = None) -> Any:
    """
    Convert any object to a JSON-serializable format.

    Handles SQLAlchemy models, Pydantic models, datetime objects,
    and complex nested structures while preventing circular references.

    Args:
        obj: The object to serialize
        _seen: Set of object IDs to prevent circular references

    Returns:
        JSON-serializable representation of the object
    """
    # Initialize seen set for circular reference detection
    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return "<circular_reference>"

    # Add to seen set
    _seen.add(obj_id)

    try:
        # Handle primitives first (most common case)
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj

        # Handle datetime objects
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()

        # Handle Decimal
        if isinstance(obj, Decimal):
            return float(obj)

        # Handle collections
        if isinstance(obj, dict):
            return {
                str(k): convert_to_serializable(v, _seen)
                for k, v in obj.items()
            }

        if isinstance(obj, (list, tuple)):
            return [convert_to_serializable(item, _seen) for item in obj]

        if isinstance(obj, set):
            return [convert_to_serializable(item, _seen) for item in obj]

        # Handle Pydantic models (v2 preferred, v1 fallback)
        if hasattr(obj, "model_dump"):
            try:
                # Pydantic v2
                return convert_to_serializable(obj.model_dump(), _seen)
            except Exception:
                pass

        if hasattr(obj, "dict"):
            try:
                # Pydantic v1
                return convert_to_serializable(obj.dict(), _seen)
            except Exception:
                pass

        # Handle SQLAlchemy models
        if is_sqlalchemy_model(obj):
            data: Dict[str, Any] = {}
            try:
                # Get table columns
                if hasattr(obj, "__table__"):
                    for col in obj.__table__.columns:
                        col_value = getattr(obj, col.name, None)
                        data[col.name] = convert_to_serializable(
                            col_value, _seen)

                # Add relationships and other attributes
                for key, value in obj.__dict__.items():
                    if not key.startswith("_") and key not in data:
                        # Avoid loading lazy-loaded relationships unnecessarily
                        try:
                            data[key] = convert_to_serializable(value, _seen)
                        except Exception:
                            # Skip attributes that can't be serialized
                            continue

                return data
            except Exception as e:
                # Fallback to string representation if serialization fails
                return f"<SQLAlchemy model: {type(obj).__name__}>"

        # Handle dataclasses
        if hasattr(obj, "__dataclass_fields__"):
            return {
                field.name: convert_to_serializable(
                    getattr(obj, field.name), _seen)
                for field in obj.__dataclass_fields__.values()
            }

        # Handle named tuples
        if hasattr(obj, "_fields"):
            return {
                field: convert_to_serializable(getattr(obj, field), _seen)
                for field in obj._fields
            }

        # Try orjson for better performance if available
        if HAS_ORJSON:
            try:
                # orjson can handle many types natively
                return orjson.loads(orjson.dumps(obj, default=str, option=ORJSON_OPTIONS))
            except Exception:
                pass

        # Final fallback: convert to string
        return str(obj)

    except Exception:
        # Ultimate fallback
        return f"<{type(obj).__name__}>"

    finally:
        # Remove from seen set to allow reuse in other branches
        _seen.discard(obj_id)


def get_environment_info() -> Dict[str, Any]:
    """Get information about the current environment."""
    return {
        "is_pyodide": IS_PYODIDE,
        "python_version": sys.version,
        "platform": sys.platform if not IS_PYODIDE else "pyodide",
        "has_sqlalchemy": HAS_SQLALCHEMY,
        "has_orjson": HAS_ORJSON,
        "sqlalchemy_registry_support": HAS_SQLALCHEMY_REGISTRY,
    }


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely serialize an object to JSON string.

    Uses orjson if available for better performance, otherwise falls back to
    the standard json module.
    """
    try:
        serializable_obj = convert_to_serializable(obj)

        if HAS_ORJSON:
            # Use orjson for better performance
            options = kwargs.pop('option', ORJSON_OPTIONS)
            return orjson.dumps(serializable_obj, option=options).decode('utf-8')
        else:
            # Fallback to standard json
            import json
            return json.dumps(serializable_obj, **kwargs)

    except Exception as e:
        # Return error information as JSON
        import json
        return json.dumps({
            "error": "Serialization failed",
            "message": str(e),
            "type": type(obj).__name__
        })


def compute_object_hash(obj: Any) -> str:
    """
    Compute a hash for an object for caching purposes.

    This is useful for detecting when objects have changed.
    """
    import hashlib

    try:
        # Convert to stable string representation
        serialized = safe_json_dumps(obj, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:16]
    except Exception:
        # Fallback to type and id
        return hashlib.sha256(f"{type(obj).__name__}_{id(obj)}".encode()).hexdigest()[:16]
