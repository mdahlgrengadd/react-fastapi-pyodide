"""Post domain service layer."""
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.domains.models import Post
from app.domains.posts.schemas import PostCreate, PostUpdate


class PostService:
    """Service layer for post operations."""

    def __init__(self, db: Union[Session, AsyncSession]):
        self.db = db

    async def get_posts(self, skip: int = 0, limit: int = 100) -> List[Post]:
        """Get all posts with pagination."""
        if isinstance(self.db, AsyncSession):
            stmt = select(Post).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        else:
            return self.db.query(Post).offset(skip).limit(limit).all()

    async def get_post(self, post_id: int) -> Optional[Post]:
        """Get post by ID."""
        if isinstance(self.db, AsyncSession):
            stmt = select(Post).where(Post.id == post_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            return self.db.query(Post).filter(Post.id == post_id).first()

    async def get_posts_by_user(self, user_id: int) -> List[Post]:
        """Get all posts by a specific user."""
        if isinstance(self.db, AsyncSession):
            stmt = select(Post).where(Post.author_id == user_id)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        else:
            return self.db.query(Post).filter(Post.author_id == user_id).all()

    async def create_post(self, post: PostCreate) -> Post:
        """Create a new post."""
        db_post = Post(**post.dict())
        self.db.add(db_post)

        if isinstance(self.db, AsyncSession):
            await self.db.commit()
            await self.db.refresh(db_post)
        else:
            self.db.commit()
            self.db.refresh(db_post)
        return db_post

    async def update_post(self, post_id: int, post_update: PostUpdate) -> Optional[Post]:
        """Update an existing post."""
        db_post = await self.get_post(post_id)
        if db_post:
            update_data = post_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_post, field, value)

            if isinstance(self.db, AsyncSession):
                await self.db.commit()
                await self.db.refresh(db_post)
            else:
                self.db.commit()
                self.db.refresh(db_post)
        return db_post

    async def delete_post(self, post_id: int) -> bool:
        """Delete a post."""
        db_post = await self.get_post(post_id)
        if db_post:
            if isinstance(self.db, AsyncSession):
                await self.db.delete(db_post)
                await self.db.commit()
            else:
                self.db.delete(db_post)
                self.db.commit()
            return True
        return False

    async def get_post_count(self) -> int:
        """Get total post count."""
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count(Post.id))
            result = await self.db.execute(stmt)
            return result.scalar()
        else:
            return self.db.query(Post).count()

    async def get_published_post_count(self) -> int:
        """Get published post count."""
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count(Post.id)).where(Post.published == True)
            result = await self.db.execute(stmt)
            return result.scalar()
        else:
            return self.db.query(Post).filter(Post.published == True).count()
