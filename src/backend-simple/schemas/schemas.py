# Pydantic schemas for request/response validation
from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Model for creating a new user"""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., description="Valid email address")
    age: Optional[int] = Field(None, ge=0, le=150)
    bio: Optional[str] = Field(None, max_length=1000)


class UserUpdate(BaseModel):
    """Model for updating a user"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    bio: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class PostCreate(BaseModel):
    """Model for creating a new post"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    published: bool = Field(False)
    author_id: int


class PostUpdate(BaseModel):
    """Model for updating a post"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    published: Optional[bool] = None
