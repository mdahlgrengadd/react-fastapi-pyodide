"""Post domain schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    """Schema for creating a new post."""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    published: bool = Field(False)
    author_id: int


class PostUpdate(BaseModel):
    """Schema for updating a post."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    published: Optional[bool] = None


class PostResponse(BaseModel):
    """Schema for post response."""
    id: int
    title: str
    content: str
    published: bool
    author_id: int
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True
