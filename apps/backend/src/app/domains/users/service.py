"""User domain service layer."""
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.domains.models import User, Post
from app.domains.users.schemas import UserCreate, UserUpdate


class UserService:
    """Service layer for user operations."""

    def __init__(self, db: Union[Session, AsyncSession]):
        self.db = db

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        if isinstance(self.db, AsyncSession):
            stmt = select(User).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        else:
            return self.db.query(User).offset(skip).limit(limit).all()

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        if isinstance(self.db, AsyncSession):
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            return self.db.query(User).filter(User.id == user_id).first()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        if isinstance(self.db, AsyncSession):
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            return self.db.query(User).filter(User.email == email).first()

    async def create_user(self, user: UserCreate) -> User:
        """Create a new user."""
        db_user = User(**user.dict())
        self.db.add(db_user)

        if isinstance(self.db, AsyncSession):
            await self.db.commit()
            await self.db.refresh(db_user)
        else:
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        db_user = await self.get_user(user_id)
        if db_user:
            update_data = user_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_user, field, value)

            if isinstance(self.db, AsyncSession):
                await self.db.commit()
                await self.db.refresh(db_user)
            else:
                self.db.commit()
                self.db.refresh(db_user)
        return db_user

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        db_user = await self.get_user(user_id)
        if db_user:
            if isinstance(self.db, AsyncSession):
                await self.db.delete(db_user)
                await self.db.commit()
            else:
                self.db.delete(db_user)
                self.db.commit()
            return True
        return False

    async def search_users(self, search: str) -> List[User]:
        """Search users by name or email."""
        # Ensure search is a string and not None
        if not search or not isinstance(search, str):
            return []
        
        search_term = search.strip().lower()
        if not search_term:
            return []
            
        if isinstance(self.db, AsyncSession):
            stmt = select(User).where(
                func.lower(User.name).contains(search_term) |
                func.lower(User.email).contains(search_term)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        else:
            return self.db.query(User).filter(
                func.lower(User.name).contains(search_term) |
                func.lower(User.email).contains(search_term)
            ).all()

    async def get_user_count(self) -> int:
        """Get total user count."""
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count(User.id))
            result = await self.db.execute(stmt)
            return result.scalar()
        else:
            return self.db.query(User).count()

    async def get_active_user_count(self) -> int:
        """Get active user count."""
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count(User.id)).where(User.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalar()
        else:
            return self.db.query(User).filter(User.is_active == True).count()

    async def get_posts_by_user(self, user_id: int) -> List[Post]:
        """Get all posts by a specific user."""
        if isinstance(self.db, AsyncSession):
            stmt = select(Post).where(Post.author_id ==
                                      user_id).order_by(Post.created_at.desc())
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        else:
            return self.db.query(Post).filter(Post.author_id == user_id).order_by(Post.created_at.desc()).all()
