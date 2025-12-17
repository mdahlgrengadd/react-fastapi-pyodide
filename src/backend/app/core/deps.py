"""Core dependencies."""
from typing import AsyncGenerator, Generator, Union
from fastapi import Depends

from app.db.session import get_db as get_db_session, HAS_ASYNC_SQLALCHEMY, IS_PYODIDE
from app.core.security import get_current_user as get_current_user_impl, get_current_user_sync

# Database dependency
# IMPORTANT: In Pyodide, we MUST use async generators even for sync DB operations
# because FastAPI runs sync dependencies in a thread pool (via run_in_executor),
# which fails in Pyodide's single-threaded browser environment.
if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
    # Use async database session for CPython
    async def get_db() -> AsyncGenerator:
        async for session in get_db_session():
            yield session
else:
    # Use async wrapper around sync database session for Pyodide
    # This prevents FastAPI from trying to run it in a thread pool
    async def get_db() -> AsyncGenerator:
        for session in get_db_session():
            yield session


# User dependency functions
if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
    get_current_user = get_current_user_impl
else:
    # Wrap sync function as async to avoid thread pool execution in Pyodide
    async def get_current_user():
        return get_current_user_sync()
