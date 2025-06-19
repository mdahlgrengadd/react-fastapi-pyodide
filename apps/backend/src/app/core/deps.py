"""Core dependencies."""
from typing import AsyncGenerator, Generator, Union
from fastapi import Depends

from app.db.session import get_db as get_db_session, HAS_ASYNC_SQLALCHEMY, IS_PYODIDE
from app.core.security import get_current_user as get_current_user_impl, get_current_user_sync

# Database dependency
if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
    # Use async database session for CPython
    async def get_db() -> AsyncGenerator:
        async for session in get_db_session():
            yield session
else:
    # Use sync database session for Pyodide
    def get_db() -> Generator:
        yield from get_db_session()


# User dependency functions
if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
    get_current_user = get_current_user_impl
else:
    get_current_user = get_current_user_sync
