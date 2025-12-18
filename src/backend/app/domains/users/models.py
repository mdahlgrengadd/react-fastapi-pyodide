"""User domain models."""
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, Relationship

from app.reactive_sqlmodel import ReactiveModel


class User(ReactiveModel, table=True):
    """User model with relationships."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(max_length=255, unique=True, index=True)
    age: Optional[int] = None
    is_active: bool = True
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to posts - use string reference for late binding
    # Note: Relationships are optional in SQLModel for tables
    # posts: List["Post"] = Relationship(back_populates="author", cascade_delete=True)

    @staticmethod
    def __topics__(user: "User") -> list[str]:
        """Define topics for this user.

        Returns list of topic strings that this user belongs to.
        Used for reactive sync subscriptions.
        """
        return [f"user:{user.id}"]
