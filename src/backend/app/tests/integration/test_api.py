"""Integration tests for the FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import create_app
from db.base import Base
from core.deps import get_db


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = SessionLocal()
            yield db
        finally:
            db.close()

    return override_get_db


@pytest.fixture
def client(test_db):
    """Create test client with test database."""
    app = create_app()
    app.dependency_overrides[get_db] = test_db

    with TestClient(app) as test_client:
        yield test_client


def test_read_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Welcome" in data["message"]


def test_create_user(client):
    """Test user creation endpoint."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "age": 25,
        "bio": "Test bio"
    }

    response = client.post("/users", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["age"] == 25


def test_get_users(client):
    """Test getting users."""
    # First create a user
    user_data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    client.post("/users", json=user_data)

    # Get users
    response = client.get("/users")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_user_by_id(client):
    """Test getting a specific user."""
    # First create a user
    user_data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    create_response = client.post("/users", json=user_data)
    created_user = create_response.json()

    # Get the user by ID
    response = client.get(f"/users/{created_user['id']}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_user["id"]
    assert data["name"] == "Test User"


def test_update_user(client):
    """Test updating a user."""
    # First create a user
    user_data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    create_response = client.post("/users", json=user_data)
    created_user = create_response.json()

    # Update the user
    update_data = {
        "name": "Updated User",
        "age": 30
    }
    response = client.put(f"/users/{created_user['id']}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Updated User"
    assert data["age"] == 30


def test_system_info(client):
    """Test system info endpoint."""
    response = client.get("/system/info")
    assert response.status_code == 200

    data = response.json()
    assert "system" in data
    assert "user" in data
    assert "database" in data
