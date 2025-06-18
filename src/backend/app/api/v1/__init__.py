"""API v1 router aggregation."""
from fastapi import APIRouter

from domains.users.router import router as users_router
from domains.posts.router import router as posts_router
from domains.dashboard.router import router as dashboard_router
from domains.system.router import router as system_router

# Create the main v1 router
router = APIRouter()

# Include all domain routers
router.include_router(users_router, tags=["users"])
router.include_router(posts_router, tags=["posts"])
router.include_router(dashboard_router, tags=["dashboard"])
router.include_router(system_router, tags=["system"])
