"""Database initialization and sample data setup."""
from typing import Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import text

from .base import Base
from .session import engine, get_db_sync, DATABASE_URL, ENVIRONMENT, HAS_ASYNC_SQLALCHEMY
from core.logging import get_logger
from core.runtime import IS_PYODIDE

logger = get_logger(__name__)


async def create_tables():
    """Create all database tables."""
    try:
        # Import all models to ensure they're registered
        from domains.users.models import User
        from domains.posts.models import Post

        if HAS_ASYNC_SQLALCHEMY and not IS_PYODIDE:
            # Async engine - use async context manager
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            # Sync engine - use sync method
            Base.metadata.create_all(bind=engine)

        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def create_tables_sync():
    """Synchronous version of create_tables for compatibility."""
    try:        # Import all models to ensure they're registered
        from domains.users.models import User
        from domains.posts.models import Post

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (sync)")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def init_sample_data(db: Session) -> Dict[str, Any]:
    """Initialize database with sample data (only if not already persisted)."""
    try:        # Import models
        from domains.users.models import User
        from domains.posts.models import Post

        # Check if data already exists (from persistence)
        existing_users = db.query(User).count()
        existing_posts = db.query(Post).count()

        if existing_users > 0:
            logger.info(
                f"Found {existing_users} users and {existing_posts} posts from persistent storage!")
            return {"loaded_from_persistence": True, "users": existing_users, "posts": existing_posts}

        logger.info(
            "No existing data found - initializing fresh sample data...")

        # Create sample users
        users_data = [
            {"name": "Alice Johnson", "email": "alice@example.com",
                "age": 30, "bio": "Software engineer who loves FastAPI"},
            {"name": "Bob Smith", "email": "bob@example.com",
                "age": 25, "bio": "Data scientist exploring Pyodide"},
            {"name": "Charlie Brown", "email": "charlie@example.com",
                "age": 35, "bio": "Product manager building web apps"},
            {"name": "Diana Prince", "email": "diana@example.com",
                "age": 28, "bio": "UX designer passionate about user experience"},
            {"name": "Eve Wilson", "email": "eve@example.com",
                "age": 32, "bio": "DevOps engineer optimizing workflows"},
        ]

        created_users = []
        for user_data in users_data:
            user = User(**user_data)
            db.add(user)
            created_users.append(user)

        db.commit()

        # Refresh to get IDs
        for user in created_users:
            db.refresh(user)

        # Create sample posts
        posts_data = [
            {"title": "Welcome to Persistent FastAPI", "content": "This FastAPI demo now uses persistent storage! Data survives page reloads.",
                "author_id": created_users[0].id, "published": True},
            {"title": "SQLAlchemy + Pyodide Magic", "content": "Running SQLAlchemy with persistent databases entirely in the browser is amazing!",
                "author_id": created_users[1].id, "published": True},
            {"title": "Building Web Apps with No Backend", "content": "With persistent Pyodide, you can build full-stack apps that run entirely client-side.",
                "author_id": created_users[2].id, "published": False},
            {"title": "Data Science Meets Web Development", "content": "Pyodide bridges Python data science and web development beautifully.",
                "author_id": created_users[1].id, "published": True},
            {"title": "The Future of Client-Side Apps", "content": "Persistent storage in the browser opens up incredible possibilities.",
                "author_id": created_users[3].id, "published": True},
            {"title": "DevOps in the Browser", "content": "Managing persistent data without servers is a game-changer for deployment.",
                "author_id": created_users[4].id, "published": True},
            {"title": "Draft: More Ideas Coming", "content": "This is a draft post to show unpublished content.",
                "author_id": created_users[0].id, "published": False},
        ]

        for post_data in posts_data:
            post = Post(**post_data)
            db.add(post)

        db.commit()
        logger.info(
            f"Created {len(users_data)} users and {len(posts_data)} posts")
        return {"loaded_from_persistence": False, "users": len(users_data), "posts": len(posts_data)}

    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing sample data: {e}")
        return {"error": str(e)}


async def init_db():
    """Initialize database and sample data."""
    logger.info("Initializing database...")

    # Create tables
    await create_tables()

    # Initialize sample data
    db = get_db_sync()
    try:
        init_result = init_sample_data(db)

        if init_result.get("loaded_from_persistence"):
            logger.info(
                f"Persistence Status: ACTIVE - Loaded {init_result['users']} users and {init_result['posts']} posts from storage")
        elif init_result.get("error"):
            logger.error(f"Persistence Status: ERROR - {init_result['error']}")
        else:
            logger.info(
                f"Persistence Status: FRESH - Created {init_result['users']} users and {init_result['posts']} posts")
    finally:
        db.close()

    logger.info("Database initialization complete!")


def init_db_sync():
    """Synchronous version of init_db for compatibility."""
    logger.info("Initializing database (sync)...")

    # Create tables
    create_tables_sync()

    # Initialize sample data
    db = get_db_sync()
    try:
        init_result = init_sample_data(db)

        if init_result.get("loaded_from_persistence"):
            logger.info(
                f"Persistence Status: ACTIVE - Loaded {init_result['users']} users and {init_result['posts']} posts from storage")
        elif init_result.get("error"):
            logger.error(f"Persistence Status: ERROR - {init_result['error']}")
        else:
            logger.info(
                f"Persistence Status: FRESH - Created {init_result['users']} users and {init_result['posts']} posts")
    finally:
        db.close()

    logger.info("Database initialization complete (sync)!")
