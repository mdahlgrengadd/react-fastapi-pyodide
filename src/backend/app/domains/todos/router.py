"""Todo API routes."""
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.domains.todos.schemas import TodoCreate, TodoResponse, TodoSummary, TodoUpdate
from app.domains.todos.service import TodoService

router = APIRouter()


@router.get("/",
            summary="Welcome to the Todo API",
            operation_id="read_root")
async def read_root() -> dict:
    """Landing endpoint describing available todo actions."""
    return {
        "message": "Welcome to the Todo API demo running inside Pyodide!",
        "endpoints": {
            "list": "/todos",
            "create": "/todos (POST)",
            "details": "/todos/{todo_id}",
            "update": "/todos/{todo_id} (PUT)",
            "toggle": "/todos/{todo_id}/toggle",
            "summary": "/todos/summary",
        },
    }


@router.get("/todos",
            response_model=List[TodoResponse],
            summary="List todos",
            operation_id="list_todos")
async def list_todos(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return"),
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> List[TodoResponse]:
    """Return todos with optional filters."""
    service = TodoService(db)
    return await service.list_todos(completed=completed, search=search, skip=skip, limit=limit)


@router.get("/todos/summary",
            response_model=TodoSummary,
            summary="Todo summary",
            operation_id="todo_summary")
async def todo_summary(
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> TodoSummary:
    """Return counts of total, completed, and pending todos."""
    service = TodoService(db)
    return await service.get_summary()


@router.get("/todos/{todo_id}",
            response_model=TodoResponse,
            summary="Get a todo",
            operation_id="get_todo")
async def get_todo(
    todo_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> TodoResponse:
    """Fetch a single todo by ID."""
    service = TodoService(db)
    todo = await service.get_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.post("/todos",
             response_model=TodoResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create a todo",
             operation_id="create_todo")
async def create_todo(
    todo: TodoCreate,
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> TodoResponse:
    """Create a new todo."""
    service = TodoService(db)
    return await service.create_todo(todo)


@router.put("/todos/{todo_id}",
            response_model=TodoResponse,
            summary="Update a todo",
            operation_id="update_todo")
async def update_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> TodoResponse:
    """Update an existing todo."""
    service = TodoService(db)
    todo = await service.update_todo(todo_id, todo_update)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.patch("/todos/{todo_id}/toggle",
              response_model=TodoResponse,
              summary="Toggle completion",
              operation_id="toggle_todo")
async def toggle_todo(
    todo_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> TodoResponse:
    """Flip the completed flag for a todo."""
    service = TodoService(db)
    todo = await service.toggle_completion(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/todos/{todo_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a todo",
               operation_id="delete_todo")
async def delete_todo(
    todo_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
) -> Response:
    """Delete a todo by ID."""
    service = TodoService(db)
    deleted = await service.delete_todo(todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Todo not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
