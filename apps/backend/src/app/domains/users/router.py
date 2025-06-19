"""User domain router."""
from typing import List, Union, Optional
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
            tags=["users"],
            operation_id="get_users")
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=100,
                       description="Maximum number of users to return"),
    search: Optional[str] = Query(
        None, description="Search users by name or email"),
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[UserResponse]:
    """Get all users with optional search and pagination."""
    service = UserService(db)

    # Handle search parameter - ensure it's a string or None
    search_term = None
    if search is not None and isinstance(search, str):
        search_term = search.strip() if search.strip() else None

    if search_term:
        return await service.search_users(search_term)
    else:
        return await service.get_users(skip=skip, limit=limit)


@router.get("/users/{user_id}",
            summary="Get user by ID",
            description="Returns a single user by ID",
            tags=["users"],
            operation_id="get_user")
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
             status_code=201,
             operation_id="create_user")
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
            tags=["users"],
            operation_id="update_user")
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
               tags=["users"],
               operation_id="delete_user")
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


@router.get("/users/async/profile-summary",
            summary="Async user profile summary",
            description="Generates a comprehensive profile summary with async processing",
            tags=["users"],
            operation_id="get_async_profile_summary")
async def get_async_profile_summary(
    user_id: int = Query(..., description="User ID to generate summary for"),
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate an async user profile summary with processing simulation."""
    import asyncio
    from datetime import datetime

    start_time = datetime.utcnow()
    service = UserService(db)

    # Define async processing functions
    async def get_user_info():
        """Get basic user information."""
        await asyncio.sleep(0.05)  # Simulate processing time
        user = await service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def get_user_posts():
        """Get user's posts with processing simulation."""
        await asyncio.sleep(0.08)  # Simulate data processing
        posts = await service.get_posts_by_user(user_id) if hasattr(service, 'get_posts_by_user') else []
        return posts

    async def generate_insights():
        """Generate user insights with simulated AI processing."""
        await asyncio.sleep(0.12)  # Simulate AI processing time
        return {
            "activity_level": "high",
            "engagement_score": 85,
            "content_quality": "excellent",
            "generated_at": datetime.utcnow()
        }

    # Execute all operations concurrently
    user_info_task = asyncio.create_task(get_user_info())
    user_posts_task = asyncio.create_task(get_user_posts())
    insights_task = asyncio.create_task(generate_insights())

    try:
        user_info, user_posts, insights = await asyncio.gather(
            user_info_task, user_posts_task, insights_task
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating profile summary: {str(e)}")

    end_time = datetime.utcnow()
    processing_time = (end_time - start_time).total_seconds()

    return {
        "message": "Async profile summary generated successfully",
        "requested_by": current_user,
        "profile_summary": {
            "user": user_info,
            "posts_count": len(user_posts) if user_posts else 0,
            "insights": insights,
            "summary_text": f"User {user_info.name if hasattr(user_info, 'name') else 'Unknown'} is an active member with {len(user_posts) if user_posts else 0} posts."
        },
        "processing_info": {
            "async_operations": 3,
            "processing_time_seconds": processing_time,
            "start_time": start_time,
            "end_time": end_time
        },
        "note": "This endpoint demonstrates async user data processing and concurrent operations"
    }
