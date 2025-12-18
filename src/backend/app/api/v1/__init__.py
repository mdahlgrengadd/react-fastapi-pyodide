"""API v1 router aggregation."""
from fastapi import APIRouter

from app.domains.todos.router import router as todos_router

router = APIRouter()
router.include_router(todos_router, tags=["todos"])
