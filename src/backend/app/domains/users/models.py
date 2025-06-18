"""User domain models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from db.base import Base


class User(Base):
    """User model with relationships."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    age = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to posts
    posts = relationship("Post", back_populates="author",
                         cascade="all, delete-orphan")
