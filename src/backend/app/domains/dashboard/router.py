"""Dashboard domain router."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.deps import get_db, get_current_user
from db.session import DATABASE_URL, ENVIRONMENT
from ..users.models import User
from ..posts.models import Post

router = APIRouter()


@router.get("/dashboard",
            summary="Dashboard with mixed SQLAlchemy models",
            description="Complex response combining multiple SQLAlchemy models",
            tags=["dashboard"])
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Dashboard with complex mixed SQLAlchemy model response."""
    # Get statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_posts = db.query(Post).count()
    published_posts = db.query(Post).filter(Post.published == True).count()

    # Get recent users and posts
    recent_users = db.query(User).order_by(
        User.created_at.desc()).limit(3).all()
    recent_posts = db.query(Post).order_by(
        Post.created_at.desc()).limit(3).all()

    return {
        "message": f"Welcome {current_user['name']} to the Dashboard!",
        "user_info": current_user,
        "recent_users": recent_users,
        "recent_posts": recent_posts,
        "statistics": {
            "total_users": total_users,
            "active_users": active_users,
            "total_posts": total_posts,
            "published_posts": published_posts,
            "engagement_rate": round((published_posts / total_posts * 100) if total_posts > 0 else 0, 1)
        },
        "persistence_info": {
            "enabled": "persist" in DATABASE_URL,
            "database_url": DATABASE_URL,
            "environment": ENVIRONMENT,
            "note": {
                "pyodide-persistent": "All this data survives page reloads via IndexedDB!",
                "fastapi-production": "Data persists in production database",
                "fastapi-development": "Data resets on server restart (development mode)"
            }.get(ENVIRONMENT, "Data persistence varies by environment")
        },
        "timestamp": datetime.utcnow(),
        "generated_in": {
            "pyodide-persistent": "Pyodide Browser (Persistent)",
            "fastapi-production": "FastAPI Backend (Production)",
            "fastapi-development": "FastAPI Backend (Development)"
        }.get(ENVIRONMENT, "Unknown Environment")
    }


@router.get("/analytics",
            summary="Analytics with aggregated data",
            description="Complex analytics combining SQLAlchemy queries and models",
            tags=["dashboard"])
def get_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Analytics endpoint with aggregated data."""
    # Get user analytics
    user_stats = db.query(
        func.count(User.id).label('total'),
        func.sum(func.case([(User.is_active == True, 1)], else_=0)).label(
            'active'),
        func.avg(User.age).label('avg_age')
    ).first()

    # Get post analytics
    post_stats = db.query(
        func.count(Post.id).label('total'),
        func.sum(func.case([(Post.published == True, 1)], else_=0)).label(
            'published')
    ).first()

    # Get most productive authors
    top_authors = db.query(
        User.name,
        func.count(Post.id).label('post_count')
    ).join(Post).group_by(User.id, User.name).order_by(func.count(Post.id).desc()).limit(5).all()

    return {
        "user_analytics": {
            "total_users": user_stats.total or 0,
            "active_users": user_stats.active or 0,
            "average_age": round(float(user_stats.avg_age or 0), 1)
        },
        "post_analytics": {
            "total_posts": post_stats.total or 0,
            "published_posts": post_stats.published or 0,
            "draft_posts": (post_stats.total or 0) - (post_stats.published or 0)
        },
        "top_authors": [
            {"name": author.name, "post_count": author.post_count}
            for author in top_authors
        ],
        "environment": ENVIRONMENT,
        "generated_at": datetime.utcnow()
    }
