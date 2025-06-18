# SQLAlchemy User and Post models
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

try:
    from sqlalchemy.orm import relationship
except ImportError:
    from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    """SQLAlchemy User model with relationships"""
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


class Post(Base):
    """SQLAlchemy Post model with foreign key relationship"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    published = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationship to user
    author = relationship("User", back_populates="posts")
