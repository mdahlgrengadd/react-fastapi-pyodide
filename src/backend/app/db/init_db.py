"""Database initialization and sample data setup for the Todo app."""
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, get_db_sync, DATABASE_URL, ENVIRONMENT, HAS_ASYNC_SQLALCHEMY
from app.core.logging import get_logger
from app.core.runtime import IS_PYODIDE

logger = get_logger(__name__)


async def create_tables():
    """Create all database tables."""
    try:
        from app.domains.models import Todo, configure_relationships

        configure_relationships()

        if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            Base.metadata.create_all(bind=engine)

        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def create_tables_sync():
    """Synchronous version of create_tables for compatibility."""
    try:
        from app.domains.models import Todo, configure_relationships

        configure_relationships()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (sync)")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def init_sample_data(db: Session) -> Dict[str, Any]:
    """Initialize database with sample todos (only if not already persisted)."""
    try:
        from app.domains.models import Todo

        existing_todos = db.query(Todo).count()
        if existing_todos > 0:
            logger.info(f"Found {existing_todos} todos from persistent storage")
            return {"loaded_from_persistence": True, "todos": existing_todos}

        logger.info("No existing data found - initializing sample todos...")

        todos = [
            {
                "title": "Plan the demo",
                "description": "Outline the todo API endpoints to showcase",
                "priority": "high",
                "completed": False,
            },
            {
                "title": "Build the UI",
                "description": "Wire the React frontend to the Pyodide-backed API",
                "priority": "normal",
                "completed": False,
            },
            {
                "title": "Test persistence",
                "description": "Confirm todos survive refreshes when persisted",
                "priority": "normal",
                "completed": False,
            },
            {
                "title": "Celebrate",
                "description": "Mark tasks done and toggle their status",
                "priority": "low",
                "completed": True,
            },
        ]

        for todo_data in todos:
            todo = Todo(**todo_data)
            db.add(todo)

        db.commit()

        for todo in db.query(Todo).all():
            db.refresh(todo)

        logger.info(f"Created {len(todos)} sample todos")
        return {"loaded_from_persistence": False, "todos": len(todos)}

    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing sample data: {e}")
        return {"error": str(e)}


async def init_db():
    """Initialize database and sample data."""
    logger.info("Initializing database...")

    await create_tables()

    db = get_db_sync()
    try:
        init_result = init_sample_data(db)

        if init_result.get("loaded_from_persistence"):
            logger.info(
                f"Persistence Status: ACTIVE - Loaded {init_result['todos']} todos from storage")
        elif init_result.get("error"):
            logger.error(f"Persistence Status: ERROR - {init_result['error']}")
        else:
            logger.info(
                f"Persistence Status: FRESH - Created {init_result['todos']} todos")
    finally:
        db.close()

    logger.info("Database initialization complete!")


def init_db_sync():
    """Synchronous version of init_db for compatibility."""
    logger.info("Initializing database (sync)...")

    create_tables_sync()

    db = get_db_sync()
    try:
        init_result = init_sample_data(db)

        if init_result.get("loaded_from_persistence"):
            logger.info(
                f"Persistence Status: ACTIVE - Loaded {init_result['todos']} todos from storage")
        elif init_result.get("error"):
            logger.error(f"Persistence Status: ERROR - {init_result['error']}")
        else:
            logger.info(
                f"Persistence Status: FRESH - Created {init_result['todos']} todos")
    finally:
        db.close()

    logger.info("Database initialization complete (sync)!")
