"""Unit tests for user domain."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.domains.users.models import User
from app.domains.users.service import UserService
from app.domains.users.schemas import UserCreate, UserUpdate


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_user(db_session):
    """Test user creation."""
    service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        age=25,
        bio="Test bio"
    )

    user = service.create_user(user_data)

    assert user.id is not None
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.age == 25
    assert user.is_active is True


def test_get_user(db_session):
    """Test getting user by ID."""
    service = UserService(db_session)

    # Create a user first
    user_data = UserCreate(name="Test User", email="test@example.com")
    created_user = service.create_user(user_data)

    # Get the user
    retrieved_user = service.get_user(created_user.id)

    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.name == "Test User"


def test_update_user(db_session):
    """Test user update."""
    service = UserService(db_session)

    # Create a user first
    user_data = UserCreate(name="Test User", email="test@example.com")
    created_user = service.create_user(user_data)

    # Update the user
    update_data = UserUpdate(name="Updated User", age=30)
    updated_user = service.update_user(created_user.id, update_data)

    assert updated_user is not None
    assert updated_user.name == "Updated User"
    assert updated_user.age == 30
    assert updated_user.email == "test@example.com"  # Should remain unchanged


def test_delete_user(db_session):
    """Test user deletion."""
    service = UserService(db_session)

    # Create a user first
    user_data = UserCreate(name="Test User", email="test@example.com")
    created_user = service.create_user(user_data)

    # Delete the user
    result = service.delete_user(created_user.id)
    assert result is True

    # Verify deletion
    deleted_user = service.get_user(created_user.id)
    assert deleted_user is None


def test_search_users(db_session):
    """Test user search functionality."""
    service = UserService(db_session)

    # Create test users
    users_data = [
        UserCreate(name="Alice Smith", email="alice@example.com"),
        UserCreate(name="Bob Johnson", email="bob@example.com"),
        UserCreate(name="Charlie Brown", email="charlie@test.com"),
    ]

    for user_data in users_data:
        service.create_user(user_data)

    # Search by name
    results = service.search_users("alice")
    assert len(results) == 1
    assert results[0].name == "Alice Smith"

    # Search by email domain
    results = service.search_users("example.com")
    assert len(results) == 2
