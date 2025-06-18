# Database configuration and utilities
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

# Base class for all SQLAlchemy models
Base = declarative_base()

# Database setup - intelligent environment detection


def get_database_url():
    """Get the appropriate database URL based on environment"""
    try:
        # First priority: Use persistent database URL (Pyodide environment)
        DATABASE_URL = get_persistent_db_url()
        ENVIRONMENT = "pyodide-persistent"
        print(f" Using Pyodide persistent database: {DATABASE_URL}")
        return DATABASE_URL, ENVIRONMENT
    except (NameError, AttributeError):
        # Second priority: Check for environment variable (production FastAPI)
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            ENVIRONMENT = "fastapi-production"
            print(
                f" Using production database from DATABASE_URL: {DATABASE_URL}")
            return DATABASE_URL, ENVIRONMENT
        else:
            # Final fallback: Temporary file database (development/demo)
            # Use temp file instead of :memory: to ensure shared database
            # Use temp file instead of :memory:
            DATABASE_URL = "sqlite:///temp_dev.db"
            ENVIRONMENT = "fastapi-development"
            print(" Using temporary file database (development mode)")
            return DATABASE_URL, ENVIRONMENT


# Initialize database
DATABASE_URL, ENVIRONMENT = get_database_url()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Standard FastAPI database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print(" SQLAlchemy database and relationships setup complete")
