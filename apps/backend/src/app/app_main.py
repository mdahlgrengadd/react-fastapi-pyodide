"""
Main FastAPI application using the pyodide-bridge-py package.

This is the migrated version that uses the clean FastAPIBridge class
instead of monkey-patched FastAPI.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

# Use the new bridge package instead of the old bridge code
from pyodide_bridge import FastAPIBridge

from app.core.deps import get_db, get_current_user
from app.core.logging import setup_logging, get_logger
from app.core.settings import settings
from app.db.init_db import init_db, init_db_sync
from app.db.session import HAS_ASYNC_SQLALCHEMY, IS_PYODIDE

# Import domain routers
from app.api.v1 import router as api_v1_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPIBridge):
    """
    Application lifespan events.

    This handles initialization and cleanup for the FastAPI bridge application.
    """
    # Startup
    logger.info("Starting FastAPI Bridge application...")

    # Initialize database
    if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
        await init_db()
    else:
        init_db_sync()

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Application shutdown complete")


def create_app() -> FastAPIBridge:
    """
    Create the FastAPI application using the bridge.

    Returns:
        FastAPIBridge instance configured with all routes and middleware
    """
    # Setup logging
    setup_logging(debug=settings.debug)

    # Create FastAPI bridge instance (extends FastAPI)
    app = FastAPIBridge(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan
    )

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
        """Welcome endpoint showcasing the new bridge implementation."""
        return {
            "message": f"Welcome {current_user['name']} to the FastAPI Bridge Demo!",
            "bridge_version": "0.1.0",
            "using_package": "pyodide-bridge-py",
            "environment": current_user["environment"],
            "features": [
                "Clean FastAPIBridge inheritance",
                "No monkey-patching",
                "Automatic route registration",
                "operation_id enforcement",
                "Improved serialization",
                "Streaming support"
            ]
        }

    # Add bridge-specific endpoints
    @app.get("/bridge/endpoints",
             operation_id="get_bridge_endpoints",
             summary="Get bridge endpoints",
             tags=["bridge"])
    async def get_bridge_endpoints():
        """Get list of registered bridge endpoints."""
        return app.get_endpoints()

    @app.get("/bridge/registry",
             operation_id="get_bridge_registry",
             summary="Get bridge registry",
             tags=["bridge"])
    async def get_bridge_registry():
        """Get the internal bridge registry for debugging."""
        return app.get_registry()

    @app.post("/bridge/invoke/{operation_id}",
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
        return await app.invoke(
            operation_id=operation_id,
            path_params=path_params or {},
            query_params=query_params or {},
            body=body
        )

    logger.info(
        f"FastAPI Bridge application created with {len(app.get_endpoints())} endpoints")

    return app


# Create the app instance
app = create_app()

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
