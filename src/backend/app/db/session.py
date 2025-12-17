"""Async database session management."""
import os
from typing import AsyncGenerator

try:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine
    )
    # Test if aiosqlite is available
    import aiosqlite
    HAS_ASYNC_SQLALCHEMY = True
except ImportError:
    # Fallback for environments without async SQLAlchemy or aiosqlite
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session as SyncSession
    HAS_ASYNC_SQLALCHEMY = False

from app.core.runtime import is_pyodide, get_environment
from app.core.logging import get_logger

logger = get_logger(__name__)

# Export IS_PYODIDE as a constant for other modules to import
IS_PYODIDE = is_pyodide()


def get_database_url() -> tuple[str, str]:
    """Get the appropriate database URL based on environment."""
    env = get_environment()

    if is_pyodide():
        try:
            # Use persistent database URL in Pyodide environment
            # This function will be available in the Pyodide context when bridge is loaded
            DATABASE_URL = globals().get('get_persistent_db_url',
                                         lambda: "sqlite:///temp_pyodide.db")()
            logger.info(f"Using Pyodide persistent database: {DATABASE_URL}")
            return DATABASE_URL, env
        except (NameError, AttributeError):
            # Fallback to memory database
            DATABASE_URL = "sqlite:///temp_pyodide.db"
            logger.info("Using temporary Pyodide database (development mode)")
            return DATABASE_URL, env
    else:
        # CPython environment
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            logger.info(
                f"Using production database from DATABASE_URL: {DATABASE_URL}")
            return DATABASE_URL, env
        else:
            # Development fallback
            DATABASE_URL = "sqlite:///./temp_dev.db"
            logger.info("Using temporary file database (development mode)")
            return DATABASE_URL, env


# Initialize database URL and environment
DATABASE_URL, ENVIRONMENT = get_database_url()

if HAS_ASYNC_SQLALCHEMY and not is_pyodide():
    # Use async SQLAlchemy for CPython
    # Convert sync SQLite URL to async for local development
    async_url = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    engine = create_async_engine(async_url, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()
else:
    # Use sync SQLAlchemy for Pyodide or environments without async support
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    # Pyodide doesn't support threading, so we need special configuration
    engine_kwargs = {
        "connect_args": {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    }
    
    if is_pyodide():
        # Use NullPool to completely disable connection pooling in Pyodide
        # This avoids all threading issues by creating fresh connections each time
        engine_kwargs["poolclass"] = NullPool
        engine_kwargs["connect_args"]["check_same_thread"] = False
        logger.info("Using NullPool for Pyodide (no threading)")
    
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        """Get sync database session."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


def get_db_sync():
    """Get synchronous database session for compatibility."""
    if not is_pyodide() and HAS_ASYNC_SQLALCHEMY:
        # In CPython with async support, we need a sync session for certain operations
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import NullPool
        
        sync_engine_kwargs = {
            "connect_args": {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        }
        
        # Also use NullPool here to avoid threading issues
        if is_pyodide():
            sync_engine_kwargs["poolclass"] = NullPool
            logger.info("Using NullPool for sync engine (no threading)")
        
        sync_engine = create_engine(
            DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///"),
            **sync_engine_kwargs
        )
        SyncSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=sync_engine)
        return SyncSessionLocal()
    else:
        # Use existing sync session maker
        return SessionLocal()
