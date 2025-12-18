"""
Client-side FastAPI application for Pyodide.

This is a separate entry point that uses mount_client() instead of mount_server().
It connects to the server for sync but maintains a local SQLite cache.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine

from app.core.settings import settings
from app.core.logging import setup_logging, get_logger
from app.domains.models import User, Post, configure_relationships
from app.api import v1_router
from app.reactive_sqlmodel import mount_client
from app.reactive_sqlmodel.transport import PyodideTransport

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for client."""
    # Startup
    logger.info("Starting up client application (Pyodide)...")
    setup_logging(settings.debug)

    # Configure models
    configure_relationships()

    logger.info("Client application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down client application...")


def build_client_app() -> FastAPI:
    """Create and configure the client-side FastAPI application.

    This version uses mount_client() for reactive sync to the server.
    """

    # Create FastAPI instance
    app = FastAPI(
        title=f"{settings.app_name} (Client)",
        description="Client-side app with reactive sync",
        version=settings.app_version,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "users", "description": "User management (synced)"},
            {"name": "posts", "description": "Blog posts (synced)"},
            {"name": "dashboard", "description": "Complex responses"},
            {"name": "system", "description": "System information"},
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

    # Include API router (same routes as server)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    # Local SQLite engine for client-side cache
    # This will use the persistent database URL from PyodidePersistence
    try:
        # Try to get persistent database URL from global
        db_url = globals().get('get_persistent_db_url', lambda: "sqlite:///local.db")()
        logger.info(f"Using client database: {db_url}")
    except Exception:
        db_url = "sqlite:///local.db"
        logger.info("Using default client database: local.db")

    local_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )

    # Get transport from JavaScript global (set by PyodideEngine.ts)
    try:
        import js
        js_transport = js.REACTIVE_TRANSPORT
        print("✅ Got REACTIVE_TRANSPORT from JavaScript")
        logger.info("✅ Got REACTIVE_TRANSPORT from JavaScript")
    except AttributeError:
        print("⚠️ REACTIVE_TRANSPORT not found in JavaScript globals")
        logger.warning("⚠️ REACTIVE_TRANSPORT not found in JavaScript globals")
        logger.warning(
            "Make sure PyodideEngine.ts has initialized the transport")
        # Create a dummy transport for testing
        js_transport = None

    if js_transport:
        transport = PyodideTransport(js_transport)

        # Mount client-side reactive sync
        mount_client(
            app,
            local_engine=local_engine,
            models=[User, Post],
            transport=transport,
        )

        print("✅ Reactive sync client mounted")
        print("   - Local cache: SQLite")
        print("   - Sync tables: Checkpoint, Mutation")
        print("   - Models: User, Post")
        logger.info("✅ Reactive sync client mounted")
        logger.info("   - Local cache: SQLite")
        logger.info("   - Sync tables: Checkpoint, Mutation")
        logger.info("   - Models: User, Post")
        logger.info("   - Handle poke: app.state.handle_poke(topic)")
    else:
        print("⚠️ Reactive sync NOT mounted (no transport)")
        print("   App will work but changes won't sync to server")
        logger.warning("⚠️ Reactive sync NOT mounted (no transport)")
        logger.warning("App will work but changes won't sync to server")

    return app


# Create the app instance
# This will be imported by Pyodide via: from app.client_main import app
app = build_client_app()

logger.info("✅ Client app ready for Pyodide")
