"""
Main FastAPI application using the pyodide-bridge-py package.

This uses the enhanced FastAPI class from pyodide-bridge that provides
seamless Pyodide integration while maintaining full FastAPI compatibility.
"""

import asyncio
from typing import Dict, Any

# Use the enhanced FastAPI class with Pyodide bridge functionality
from pyodide_bridge import FastAPI

from app.core.deps import get_db, get_current_user
from app.core.logging import setup_logging, get_logger
from app.core.settings import settings
from app.db.init_db import init_db, init_db_sync
from app.db.session import HAS_ASYNC_SQLALCHEMY, IS_PYODIDE

# Import domain routers
from app.api.v1 import router as api_v1_router

# Setup logging
setup_logging(debug=settings.debug)
logger = get_logger(__name__)


# Create FastAPI app instance with Pyodide bridge functionality
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url
)

# Initialize database immediately since we don't use lifespan
logger.info("Initializing database...")
try:
    # Always use sync initialization since we can't use async during app creation
    init_db_sync()
    logger.info("Database initialization complete")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

# Add CORS middleware
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except ImportError:
    logger.warning("CORSMiddleware not available")

# Include API routes with operation_id requirements
app.include_router(
    api_v1_router,
    prefix=settings.api_v1_prefix
)


# Add root endpoint with operation_id
@app.get("/",
         operation_id="read_root",  # Required for bridge
         summary="Welcome endpoint",
         tags=["system"])
async def read_root(current_user: Dict[str, Any] = get_current_user):
    """Welcome endpoint showcasing the enhanced FastAPI implementation."""
    # Handle case where current_user might be a function (in bridge context)
    if callable(current_user):
        try:
            current_user = await current_user() if asyncio.iscoroutinefunction(current_user) else current_user()
        except Exception:
            # Fallback user data for bridge/testing
            current_user = {
                "name": "Bridge User",
                "environment": "Pyodide"
            }

    return {
        "message": f"Welcome {current_user['name']} to the Enhanced FastAPI Demo!",
        "bridge_version": "0.1.0",
        "using_package": "pyodide-bridge-py",
        "environment": current_user["environment"],
        "features": [
            "Enhanced FastAPI with Pyodide bridge",
            "Drop-in FastAPI replacement",
            "No monkey-patching",
            "Automatic route registration",
            "operation_id enforcement",
            "Improved serialization",
            "Streaming support"
        ]}


# Log app creation
logger.info(
    f"FastAPI application (with Pyodide bridge) created with {len(app.get_endpoints())} endpoints"
)

# For development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
