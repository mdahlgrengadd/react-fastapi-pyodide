"""Integration tests for the Todo FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.app_main import create_app
from app.db.base import Base
from app.core.deps import get_db
from app.domains.todos.models import Todo


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
    assert "Todo" in data["message"]


def test_create_and_get_todo(client):
    """Create a todo and fetch it back."""
    todo_data = {
        "title": "Write integration test",
        "description": "Ensure todo creation works",
        "priority": "high",
    }

    create_response = client.post("/todos", json=todo_data)
    assert create_response.status_code == 201

    created_todo = create_response.json()
    assert created_todo["title"] == todo_data["title"]
    assert created_todo["completed"] is False

    get_response = client.get(f"/todos/{created_todo['id']}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == created_todo["id"]
    assert fetched["title"] == todo_data["title"]


def test_list_todos(client):
    """Ensure listing returns created todos."""
    client.post("/todos", json={"title": "First todo"})
    client.post("/todos", json={"title": "Second todo", "completed": True})

    response = client.get("/todos")
    assert response.status_code == 200
    todos = response.json()
    assert isinstance(todos, list)
    assert len(todos) >= 2

    completed_only = client.get("/todos", params={"completed": True})
    assert completed_only.status_code == 200
    assert all(todo["completed"] for todo in completed_only.json())


def test_update_and_toggle_todo(client):
    """Update a todo and toggle its completion."""
    create_response = client.post("/todos", json={"title": "Update me"})
    todo_id = create_response.json()["id"]

    update_response = client.put(
        f"/todos/{todo_id}", json={"title": "Updated title", "completed": True}
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Updated title"
    assert updated["completed"] is True

    toggle_response = client.patch(f"/todos/{todo_id}/toggle")
    assert toggle_response.status_code == 200
    toggled = toggle_response.json()
    assert toggled["completed"] is False


def test_delete_todo(client):
    """Delete a todo and ensure it is gone."""
    create_response = client.post("/todos", json={"title": "Delete me"})
    todo_id = create_response.json()["id"]

    delete_response = client.delete(f"/todos/{todo_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/todos/{todo_id}")
    assert get_response.status_code == 404


def test_todo_summary(client):
    """Get todo summary counts."""
    client.post("/todos", json={"title": "Incomplete todo"})
    client.post("/todos", json={"title": "Complete todo", "completed": True})

    response = client.get("/todos/summary")
    assert response.status_code == 200
    summary = response.json()

    assert "total" in summary
    assert "completed" in summary
    assert "pending" in summary
    assert summary["total"] >= summary["completed"] >= 0
