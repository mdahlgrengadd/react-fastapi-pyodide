"""System domain router."""
from datetime import datetime
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.runtime import get_environment_info
from app.db.session import DATABASE_URL, ENVIRONMENT

router = APIRouter()


@router.get("/",
            summary="Welcome to Enhanced Bridge Demo",
            tags=["system"])
def read_root(current_user: dict = Depends(get_current_user)):
    """Welcome endpoint showcasing dependency injection and persistence info."""

    # Check if we're using persistent storage
    is_persistent = "persist" in DATABASE_URL
    env_info = get_environment_info()

    return {
        "message": f"Welcome {current_user['name']} to Enhanced SQLAlchemy Bridge Demo!",
        "environment": current_user["environment"],
        "persistence": {
            "enabled": is_persistent,
            "database_url": DATABASE_URL,
            "status": "Data survives page reloads!" if is_persistent else "Using in-memory database",
            "note": "Try refreshing the page - your data will still be here!" if is_persistent else "Data will reset when you refresh the page"
        },
        "features": [
            "Direct SQLAlchemy model returns",
            "Automatic JSON serialization",
            "Full dependency injection",
            "Standard FastAPI patterns",
            "Zero code changes needed",
            "Persistent storage (survives reloads)" if is_persistent else "In-memory storage (resets on reload)"
        ],
        "endpoints": {
            "users": "/users - Get all users (SQLAlchemy list)",
            "user": "/users/1 - Get single user (SQLAlchemy model)",
            "posts": "/posts - Get all posts (with relationships)",
            "dashboard": "/dashboard - Complex mixed response",
            "persistence": "/persistence/status - Detailed persistence information",
            "docs": "/docs - Interactive API documentation"
        },
        "runtime_info": env_info
    }


@router.get("/system/info",
            summary="System information",
            description="Get system and runtime information",
            tags=["system"])
def get_system_info(current_user: dict = Depends(get_current_user)):
    """Get comprehensive system information."""
    env_info = get_environment_info()

    return {
        "system": env_info,
        "user": current_user,
        "database": {
            "url": DATABASE_URL,
            "environment": ENVIRONMENT,
            "persistent": "persist" in DATABASE_URL
        },
        "timestamp": datetime.utcnow()
    }


@router.get("/persistence/status",
            summary="Detailed persistence information",
            description="Get comprehensive information about data persistence",
            tags=["system"])
def get_persistence_status(current_user: dict = Depends(get_current_user)):
    """Get detailed persistence status information."""
    is_persistent = "persist" in DATABASE_URL
    env_info = get_environment_info()

    return {
        "persistence": {
            "enabled": is_persistent,
            "type": "IndexedDB (IDBFS)" if env_info["is_pyodide"] else "File System",
            "database_url": DATABASE_URL,
            "environment": ENVIRONMENT,
            "description": {
                "pyodide-persistent": "Data is stored in browser IndexedDB and survives page reloads",
                "fastapi-production": "Data is stored in production database",
                "fastapi-development": "Data is stored in temporary SQLite file"
            }.get(ENVIRONMENT, "Unknown environment")
        },
        "runtime": env_info,
        "user": current_user,
        "status_check": {
            "timestamp": datetime.utcnow(),
            "message": "Persistence status checked successfully"
        }
    }
