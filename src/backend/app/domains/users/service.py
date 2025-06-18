"""User domain service layer."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import User
from .schemas import UserCreate, UserUpdate


class UserService:
    """Service layer for user operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, user: UserCreate) -> User:
        """Create a new user."""
        db_user = User(**user.dict())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        db_user = self.get_user(user_id)
        if db_user:
            update_data = user_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_user, field, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        db_user = self.get_user(user_id)
        if db_user:
            self.db.delete(db_user)
            self.db.commit()
            return True
        return False

    def search_users(self, search: str) -> List[User]:
        """Search users by name or email."""
        return self.db.query(User).filter(
            func.lower(User.name).contains(search.lower()) |
            func.lower(User.email).contains(search.lower())
        ).all()

    def get_user_count(self) -> int:
        """Get total user count."""
        return self.db.query(User).count()

    def get_active_user_count(self) -> int:
        """Get active user count."""
        return self.db.query(User).filter(User.is_active == True).count()
