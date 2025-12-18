"""Unit tests for todo domain service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domains.todos.models import Todo
from app.domains.todos.schemas import TodoCreate, TodoUpdate
from app.domains.todos.service import TodoService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_create_todo(db_session):
    """Test todo creation."""
    service = TodoService(db_session)
    todo_data = TodoCreate(title="Test Todo", description="Verify creation")

    todo = await service.create_todo(todo_data)

    assert todo.id is not None
    assert todo.title == "Test Todo"
    assert todo.completed is False


@pytest.mark.asyncio
async def test_get_todo(db_session):
    """Test getting todo by ID."""
    service = TodoService(db_session)
    todo = await service.create_todo(TodoCreate(title="Fetch me"))

    fetched = await service.get_todo(todo.id)

    assert fetched is not None
    assert fetched.id == todo.id
    assert fetched.title == "Fetch me"


@pytest.mark.asyncio
async def test_update_todo(db_session):
    """Test todo update."""
    service = TodoService(db_session)
    todo = await service.create_todo(TodoCreate(title="Update target"))

    updated = await service.update_todo(
        todo.id, TodoUpdate(title="Updated", completed=True)
    )

    assert updated is not None
    assert updated.title == "Updated"
    assert updated.completed is True


@pytest.mark.asyncio
async def test_toggle_and_delete_todo(db_session):
    """Test toggling and deleting a todo."""
    service = TodoService(db_session)
    todo = await service.create_todo(TodoCreate(title="Toggle me"))

    toggled = await service.toggle_completion(todo.id)
    assert toggled is not None
    assert toggled.completed is True

    deleted = await service.delete_todo(todo.id)
    assert deleted is True
    assert await service.get_todo(todo.id) is None


@pytest.mark.asyncio
async def test_list_filters(db_session):
    """Test list filters for completed and search."""
    service = TodoService(db_session)
    await service.create_todo(TodoCreate(title="Buy milk", completed=False))
    await service.create_todo(TodoCreate(title="File taxes", completed=True))
    await service.create_todo(TodoCreate(title="Book flights", completed=False))

    completed = await service.list_todos(completed=True)
    assert all(todo.completed for todo in completed)

    search_results = await service.list_todos(search="book")
    assert len(search_results) == 1
    assert search_results[0].title == "Book flights"
