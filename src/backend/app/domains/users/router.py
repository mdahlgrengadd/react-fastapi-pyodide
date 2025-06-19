"""User domain router."""
from typing import List, Union
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.domains.models import User
from app.domains.users.schemas import UserCreate, UserUpdate, UserResponse
from app.domains.users.service import UserService

router = APIRouter()


@router.get("/users",
            summary="Get all users",
            description="Returns list of users with pagination",
            tags=["users"])
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=100,
                       description="Maximum number of users to return"),
    search: str = Query(None, description="Search users by name or email"),
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[UserResponse]:
    """Get all users with optional search and pagination."""
    service = UserService(db)

    if search:
        return await service.search_users(search)
    else:
        return await service.get_users(skip=skip, limit=limit)


@router.get("/users/{user_id}",
            summary="Get user by ID",
            description="Returns a single user by ID",
            tags=["users"])
async def get_user(
    user_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """Get a specific user by ID."""
    service = UserService(db)
    db_user = await service.get_user(user_id)

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/users",
             summary="Create new user",
             description="Creates and returns new user",
             tags=["users"],
             status_code=201)
async def create_user(
    user: UserCreate,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """Create a new user."""
    service = UserService(db)

    # Check if user with email already exists
    existing_user = await service.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    return await service.create_user(user)


@router.put("/users/{user_id}",
            summary="Update user",
            description="Updates and returns user",
            tags=["users"])
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """Update an existing user."""
    service = UserService(db)
    db_user = await service.update_user(user_id, user)

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}",
               summary="Delete user",
               description="Deletes a user",
               tags=["users"])
async def delete_user(
    user_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a user."""
    service = UserService(db)
    success = await service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}
