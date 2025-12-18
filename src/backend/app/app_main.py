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

# Import models EARLY to ensure they're available for relationship resolution
from app.domains.models import User, Post, configure_relationships

from app.core.settings import settings
from app.core.logging import setup_logging, get_logger
from app.core.runtime import IS_PYODIDE
from app.db.init_db import init_db, init_db_sync
from app.db.session import get_db_sync
from app.api import v1_router
from app.reactive_sqlmodel import mount_server

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up application...")
    setup_logging(settings.debug)

    # Ensure models are properly configured before database initialization
    configure_relationships()

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

    # Add CORS middleware FIRST (will be processed last, ensuring all responses get CORS headers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add CORS header wrapper middleware - ensures CORS headers are ALWAYS present
    @app.middleware("http")
    async def cors_header_wrapper(request, call_next):
        """Middleware wrapper that ensures CORS headers are always present, even on exceptions."""
        try:
            response = await call_next(request)
        except Exception as exc:
            # If an exception occurs, create a response with CORS headers
            from fastapi.responses import JSONResponse
            from fastapi import status
            import traceback

            logger.error(f"Exception in request handler: {exc}", exc_info=True)

            error_detail = {
                "error": str(exc),
                "type": type(exc).__name__
            }
            if settings.debug:
                error_detail["traceback"] = traceback.format_exc()

            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_detail
            )

        # Always ensure CORS headers are present
        origin = request.headers.get("origin")
        if origin:
            # Check if CORS headers are already present (from CORS middleware)
            if "Access-Control-Allow-Origin" not in response.headers:
                if "*" in settings.cors_origins:
                    response.headers["Access-Control-Allow-Origin"] = "*"
                elif origin in settings.cors_origins:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"

        return response

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request, call_next):
        import sys
        sys.stderr.write(f"[MIDDLEWARE] {request.method} {request.url.path}\n")
        sys.stderr.flush()
        logger.error(f"[MIDDLEWARE] {request.method} {request.url.path}")
        response = await call_next(request)
        return response

    # Add exception handler to ensure CORS headers on error responses
    from fastapi import Request, status
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """HTTP exception handler - CORS middleware should add headers, but ensure they're present."""
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
        # CORS middleware should handle this, but ensure headers are present
        origin = request.headers.get("origin")
        if origin and ("Access-Control-Allow-Origin" not in response.headers):
            if "*" in settings.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = "*"
            elif origin in settings.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Validation exception handler - CORS middleware should add headers."""
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()}
        )
        # CORS middleware should handle this, but ensure headers are present
        origin = request.headers.get("origin")
        if origin and ("Access-Control-Allow-Origin" not in response.headers):
            if "*" in settings.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = "*"
            elif origin in settings.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled exceptions - ensure CORS headers."""
        import traceback
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        logger.error(
            f"Request path: {request.url.path}, Method: {request.method}")
        logger.error(f"Origin header: {request.headers.get('origin', 'None')}")

        error_detail = {
            "error": str(exc),
            "type": type(exc).__name__
        }
        if settings.debug:
            error_detail["traceback"] = traceback.format_exc()

        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_detail
        )

        # Always add CORS headers - check origin or use wildcard
        origin = request.headers.get("origin")
        if "*" in settings.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin and origin in settings.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        elif origin:
            # Origin not in allowed list, but add header anyway for debugging
            response.headers["Access-Control-Allow-Origin"] = origin
            logger.warning(
                f"Origin {origin} not in allowed list, but adding CORS header anyway")

        # Always add these headers
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

        return response

    # Add test endpoint to verify logging works
    @app.post("/test-logging")
    async def test_logging():
        import sys
        sys.stderr.write("TEST ENDPOINT CALLED\n")
        sys.stderr.flush()
        logger.error("TEST ENDPOINT CALLED")
        print("TEST ENDPOINT CALLED", flush=True)
        return {"status": "logged"}

    @app.post("/debug-push")
    async def debug_push(payload: dict):
        """Debug endpoint to test push logic directly."""
        import json
        import traceback
        from pathlib import Path

        # Write to file for debugging
        debug_file = Path("debug_push.log")
        with open(debug_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"DEBUG PUSH CALLED\n")
            f.write(f"Payload: {json.dumps(payload, indent=2)}\n")
            try:
                # Try to apply mutation manually
                from app.db.session import get_db_sync
                session = get_db_sync()
                try:
                    mutation = payload.get("mutations", [{}])[0]
                    result = apply_mutation(session, mutation, None)
                    f.write(
                        f"SUCCESS: {json.dumps(result, indent=2, default=str)}\n")
                    return {"status": "success", "result": result}
                except Exception as e:
                    f.write(f"ERROR: {e}\n")
                    f.write(f"TRACEBACK: {traceback.format_exc()}\n")
                    return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
                finally:
                    session.close()
            except Exception as e:
                f.write(f"OUTER ERROR: {e}\n")
                f.write(f"TRACEBACK: {traceback.format_exc()}\n")
                return {"status": "error", "error": str(e)}

        return {"status": "logged"}

    # Include API router
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    # Mount reactive sync endpoints (server-side)
    def open_session():
        """Factory function for opening database sessions."""
        return get_db_sync()

    def get_db_sync_dep():
        """Synchronous database dependency for reactive sync endpoints."""
        db = get_db_sync()
        try:
            yield db
        finally:
            db.close()

    def apply_mutation(session, mutation: dict, user):
        """Apply a mutation from client to server database.

        Args:
            session: Database session
            mutation: Mutation dict with {id, topic, table, pk, patch}
            user: Current user (from auth, if any)

        Returns:
            dict with {topic, table, pk, row}
        """
        from app.domains.models import User, Post

        print(
            f"[apply_mutation] Processing mutation: {mutation.get('id')}", flush=True)
        print(
            f"[apply_mutation] Table: {mutation.get('table')}, PK: {mutation.get('pk')}", flush=True)

        table = mutation["table"]
        patch = mutation["patch"]
        pk = int(mutation["pk"])

        # Route to correct model based on table name
        if table == "users":
            from sqlmodel import select
            # Check if user exists on server
            existing = session.exec(select(User).where(User.id == pk)).first()
            print(
                f"[apply_mutation] User {pk} exists: {existing is not None}", flush=True)
            if existing:
                # Update existing
                print(f"[apply_mutation] Updating user {pk}", flush=True)
                print(
                    f"[apply_mutation] Current email: {existing.email}, New email: {patch.get('email')}", flush=True)
                try:
                    # Don't update id or created_at (immutable fields)
                    for key, value in patch.items():
                        if key not in ('id', 'created_at'):
                            setattr(existing, key, value)
                    obj = existing
                    print(f"[apply_mutation] Updated successfully", flush=True)
                except Exception as e:
                    print(f"[apply_mutation] Error updating: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    raise
            else:
                # New user - exclude client id, let server assign
                print(
                    f"[apply_mutation] Creating new user (excluding client id={pk})", flush=True)
                patch_no_id = {k: v for k, v in patch.items() if k != 'id'}
                print(
                    f"[apply_mutation] Patch without id: {patch_no_id}", flush=True)
                try:
                    obj = User.model_validate(patch_no_id)
                    print(f"[apply_mutation] Validated successfully", flush=True)
                except Exception as e:
                    print(
                        f"[apply_mutation] Validation error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    raise
        elif table == "posts":
            from sqlmodel import select
            existing = session.exec(select(Post).where(Post.id == pk)).first()
            if existing:
                for key, value in patch.items():
                    if key != 'id':
                        setattr(existing, key, value)
                obj = existing
            else:
                patch_no_id = {k: v for k, v in patch.items() if k != 'id'}
                obj = Post.model_validate(patch_no_id)
        else:
            raise ValueError(f"Unknown table: {table}")

        # Save to database
        print(f"[apply_mutation] Saving...", flush=True)
        try:
            session.add(obj)
            session.commit()
            session.refresh(obj)
            print(
                f"[apply_mutation] Saved! Server assigned id={obj.id}", flush=True)
        except Exception as e:
            print(f"[apply_mutation] Save failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            session.rollback()
            raise

        return {
            "topic": mutation["topic"],
            "table": table,
            "pk": str(obj.id),  # Return server-assigned id
            # Use mode='json' to serialize datetime objects
            "row": obj.model_dump(mode='json'),
        }

    # Mount server-side reactive sync
    mount_server(
        app,
        open_session=open_session,
        get_session_dep=get_db_sync_dep,
        apply_mutation=apply_mutation,
        # Future: Add auth hooks
        # get_current_user=get_current_user,
        # can_read_topic=lambda user, topic: True,
        # can_write_topic=lambda user, topic: True,
    )

    logger.info("✅ Reactive sync endpoints mounted at /_sync")

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
