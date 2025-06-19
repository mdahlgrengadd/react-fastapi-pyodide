"""Post domain router."""
from typing import List, Union
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.domains.models import Post
from app.domains.posts.schemas import PostCreate, PostUpdate, PostResponse
from app.domains.posts.service import PostService

router = APIRouter()


@router.get("/posts",
            summary="Get all posts",
            description="Returns list of posts with relationships",
            tags=["posts"],
            operation_id="get_posts")
async def get_posts(
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[PostResponse]:
    """Get all posts with author relationships."""
    service = PostService(db)
    return await service.get_posts()


@router.get("/posts/{post_id}",
            summary="Get post by ID",
            description="Returns single post with author relationship",
            tags=["posts"],
            operation_id="get_post")
async def get_post(
    post_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Get a specific post by ID."""
    service = PostService(db)
    db_post = await service.get_post(post_id)

    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return db_post


@router.post("/posts",
             summary="Create new post",
             description="Creates and returns new post",
             tags=["posts"],
             status_code=201,
             operation_id="create_post")
async def create_post(
    post: PostCreate,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> PostResponse:
    """Create a new post."""
    service = PostService(db)
    return await service.create_post(post)


@router.get("/users/{user_id}/posts",
            summary="Get user's posts",
            description="Returns list of posts by specific user",
            tags=["posts"],
            operation_id="get_user_posts")
async def get_user_posts(
    user_id: int,
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[PostResponse]:
    """Get all posts by a specific user."""
    service = PostService(db)
    return await service.get_posts_by_user(user_id)
