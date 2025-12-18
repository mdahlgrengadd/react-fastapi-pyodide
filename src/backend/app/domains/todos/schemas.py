"""Pydantic schemas for Todo resources."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TodoBase(BaseModel):
    """Shared fields for todos."""

    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = Field(default="normal", max_length=20)
    due_date: Optional[datetime] = None


class TodoCreate(TodoBase):
    """Fields required when creating a todo."""

    title: str = Field(..., min_length=1, max_length=200)
    completed: bool = False
    priority: str = Field(default="normal", max_length=20)


class TodoUpdate(TodoBase):
    """Fields that can be updated on a todo."""

    pass


class TodoResponse(TodoBase):
    """Response payload for todo endpoints."""

    title: str
    priority: str
    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TodoSummary(BaseModel):
    """Aggregated todo stats."""

    total: int
    completed: int
    pending: int
