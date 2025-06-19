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

from app.core.runtime import IS_PYODIDE, get_environment
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_database_url() -> tuple[str, str]:
    """Get the appropriate database URL based on environment."""
    env = get_environment()

    if IS_PYODIDE:
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

if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
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

    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
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
    if not IS_PYODIDE and HAS_ASYNC_SQLALCHEMY:
        # In CPython with async support, we need a sync session for certain operations
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        sync_engine = create_engine(
            DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///"),
            connect_args={
                "check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        )
        SyncSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=sync_engine)
        return SyncSessionLocal()
    else:
        # Use existing sync session maker
        return SessionLocal()
