"""Service layer for todo operations."""
from typing import List, Optional, Union
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domains.todos.models import Todo
from app.domains.todos.schemas import TodoCreate, TodoUpdate


class TodoService:
    """Encapsulates todo data access for sync/async sessions."""

    def __init__(self, db: Union[Session, AsyncSession]):
        self.db = db

    async def list_todos(
        self,
        completed: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Todo]:
        """Return todos with optional filters."""
        query = select(Todo)

        if completed is not None:
            query = query.where(Todo.completed.is_(completed))

        if search:
            pattern = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Todo.title).like(pattern),
                    func.lower(Todo.description).like(pattern),
                )
            )

        query = query.order_by(Todo.created_at.desc()).offset(skip).limit(limit)

        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(query)
            return list(result.scalars().all())
        return list(self.db.execute(query).scalars().all())

    async def get_todo(self, todo_id: int) -> Optional[Todo]:
        """Fetch a single todo by ID."""
        query = select(Todo).where(Todo.id == todo_id)

        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        return self.db.execute(query).scalar_one_or_none()

    async def create_todo(self, todo_data: TodoCreate) -> Todo:
        """Create and persist a todo."""
        todo = Todo(**todo_data.dict())
        self.db.add(todo)

        if isinstance(self.db, AsyncSession):
            await self.db.commit()
            await self.db.refresh(todo)
        else:
            self.db.commit()
            self.db.refresh(todo)
        return todo

    async def update_todo(self, todo_id: int, todo_update: TodoUpdate) -> Optional[Todo]:
        """Update an existing todo."""
        todo = await self.get_todo(todo_id)
        if not todo:
            return None

        update_data = {k: v for k, v in todo_update.dict(exclude_unset=True).items() if v is not None}
        for field, value in update_data.items():
            setattr(todo, field, value)

        if isinstance(self.db, AsyncSession):
            await self.db.commit()
            await self.db.refresh(todo)
        else:
            self.db.commit()
            self.db.refresh(todo)
        return todo

    async def toggle_completion(self, todo_id: int) -> Optional[Todo]:
        """Flip completed flag for a todo."""
        todo = await self.get_todo(todo_id)
        if not todo:
            return None

        todo.completed = not todo.completed

        if isinstance(self.db, AsyncSession):
            await self.db.commit()
            await self.db.refresh(todo)
        else:
            self.db.commit()
            self.db.refresh(todo)
        return todo

    async def delete_todo(self, todo_id: int) -> bool:
        """Delete a todo by ID."""
        todo = await self.get_todo(todo_id)
        if not todo:
            return False

        if isinstance(self.db, AsyncSession):
            await self.db.delete(todo)
            await self.db.commit()
        else:
            self.db.delete(todo)
            self.db.commit()
        return True

    async def get_summary(self) -> dict:
        """Return counts for completed and pending todos."""
        if isinstance(self.db, AsyncSession):
            total_result = await self.db.execute(select(func.count(Todo.id)))
            completed_result = await self.db.execute(
                select(func.count(Todo.id)).where(Todo.completed.is_(True))
            )
        else:
            total_result = self.db.execute(select(func.count(Todo.id)))
            completed_result = self.db.execute(
                select(func.count(Todo.id)).where(Todo.completed.is_(True))
            )

        total = total_result.scalar() or 0
        completed = completed_result.scalar() or 0
        pending = max(total - completed, 0)

        return {"total": total, "completed": completed, "pending": pending}
