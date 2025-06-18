"""Post domain service layer."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Post
from .schemas import PostCreate, PostUpdate


class PostService:
    """Service layer for post operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_posts(self, skip: int = 0, limit: int = 100) -> List[Post]:
        """Get all posts with pagination."""
        return self.db.query(Post).offset(skip).limit(limit).all()

    def get_post(self, post_id: int) -> Optional[Post]:
        """Get post by ID."""
        return self.db.query(Post).filter(Post.id == post_id).first()

    def get_posts_by_user(self, user_id: int) -> List[Post]:
        """Get all posts by a specific user."""
        return self.db.query(Post).filter(Post.author_id == user_id).all()

    def create_post(self, post: PostCreate) -> Post:
        """Create a new post."""
        db_post = Post(**post.dict())
        self.db.add(db_post)
        self.db.commit()
        self.db.refresh(db_post)
        return db_post

    def update_post(self, post_id: int, post_update: PostUpdate) -> Optional[Post]:
        """Update an existing post."""
        db_post = self.get_post(post_id)
        if db_post:
            update_data = post_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_post, field, value)
            self.db.commit()
            self.db.refresh(db_post)
        return db_post

    def delete_post(self, post_id: int) -> bool:
        """Delete a post."""
        db_post = self.get_post(post_id)
        if db_post:
            self.db.delete(db_post)
            self.db.commit()
            return True
        return False

    def get_post_count(self) -> int:
        """Get total post count."""
        return self.db.query(Post).count()

    def get_published_post_count(self) -> int:
        """Get published post count."""
        return self.db.query(Post).filter(Post.published == True).count()
