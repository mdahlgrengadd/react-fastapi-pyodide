"""Post domain models."""
from typing import Optional
from datetime import datetime
from sqlmodel import Field, Relationship

from app.reactive_sqlmodel import ReactiveModel


class Post(ReactiveModel, table=True):
    """Post model with foreign key relationship."""
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    content: str
    published: bool = False
    author_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to user - use string reference for late binding
    # Note: Relationships are optional in SQLModel for tables
    # author: Optional["User"] = Relationship(back_populates="posts")

    @staticmethod
    def __topics__(post: "Post") -> list[str]:
        """Define topics for this post.

        Returns list of topic strings that this post belongs to.
        Used for reactive sync subscriptions.
        """
        topics = []

        # Post belongs to its own topic
        if post.id:
            topics.append(f"post:{post.id}")

        # Post also belongs to the author's topic
        if post.author_id:
            topics.append(f"user:{post.author_id}")

        return topics
