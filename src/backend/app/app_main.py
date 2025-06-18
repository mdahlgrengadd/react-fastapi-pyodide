"""Main FastAPI application factory."""
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add current directory to Python path for relative imports
if __name__ != "__main__":
    # When imported as a module (e.g., by uvicorn), ensure relative imports work
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

from core.settings import settings
from core.logging import setup_logging, get_logger
from core.runtime import IS_PYODIDE
from db.init_db import init_db, init_db_sync
from api import v1_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up application...")
    setup_logging(settings.debug)

    try:
        if IS_PYODIDE:
            # Use sync initialization for Pyodide
            init_db_sync()
        else:
            # Use async initialization for CPython
            await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Create FastAPI instance
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "users", "description": "User management with SQLAlchemy models"},
            {"name": "posts", "description": "Blog posts with relationships"},
            {"name": "dashboard", "description": "Complex responses with mixed models"},
            {"name": "system", "description": "System information and diagnostics"},
        ]
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    return app


# Create the app instance (compatible with both Pyodide and uvicorn)
app = create_app()


# For uvicorn compatibility (CPython only)
if __name__ == "__main__":
    if not IS_PYODIDE:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
