"""Dashboard domain router."""
from datetime import datetime
from typing import Union
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.deps import get_db, get_current_user
from app.db.session import DATABASE_URL, ENVIRONMENT
from app.domains.models import User, Post

router = APIRouter()


@router.get("/dashboard",
            summary="Dashboard with mixed SQLAlchemy models",
            description="Complex response combining multiple SQLAlchemy models",
            tags=["dashboard"],
            operation_id="get_dashboard")
async def get_dashboard(
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Dashboard with complex mixed SQLAlchemy model response."""
    # Get statistics
    if isinstance(db, AsyncSession):
        # Async queries
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()

        active_users_result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
        active_users = active_users_result.scalar()

        total_posts_result = await db.execute(select(func.count(Post.id)))
        total_posts = total_posts_result.scalar()

        published_posts_result = await db.execute(select(func.count(Post.id)).where(Post.published == True))
        published_posts = published_posts_result.scalar()

        # Get recent users and posts
        recent_users_result = await db.execute(select(User).order_by(User.created_at.desc()).limit(3))
        recent_users = list(recent_users_result.scalars().all())

        recent_posts_result = await db.execute(select(Post).order_by(Post.created_at.desc()).limit(3))
        recent_posts = list(recent_posts_result.scalars().all())
    else:
        # Sync queries
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
            tags=["dashboard"],
            operation_id="get_analytics")
async def get_analytics(
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Analytics endpoint with aggregated data."""
    if isinstance(db, AsyncSession):
        # Async queries
        user_stats_result = await db.execute(
            select(
                func.count(User.id).label('total'),
                func.sum(func.case([(User.is_active == True, 1)], else_=0)).label(
                    'active'),
                func.avg(User.age).label('avg_age')
            )
        )
        user_stats = user_stats_result.first()

        post_stats_result = await db.execute(
            select(
                func.count(Post.id).label('total'),
                func.sum(func.case([(Post.published == True, 1)], else_=0)).label(
                    'published')
            )
        )
        post_stats = post_stats_result.first()

        # Get most productive authors
        top_authors_result = await db.execute(
            select(User.name, func.count(Post.id).label('post_count'))
            .join(Post)
            .group_by(User.id, User.name)
            .order_by(func.count(Post.id).desc())
            .limit(5)
        )
        top_authors = list(top_authors_result.all())
    else:
        # Sync queries
        user_stats = db.query(
            func.count(User.id).label('total'),
            func.sum(func.case([(User.is_active == True, 1)], else_=0)).label(
                'active'),
            func.avg(User.age).label('avg_age')
        ).first()

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


@router.get("/dashboard/async-stats",
            summary="Async dashboard statistics",
            description="Demonstrates async database queries with real-time stats",
            tags=["dashboard"],
            operation_id="get_async_dashboard_stats")
async def get_async_dashboard_stats(
    db: Union[Session, AsyncSession] = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Async endpoint demonstrating concurrent database queries."""
    import asyncio
    from datetime import datetime, timedelta

    start_time = datetime.utcnow()

    # Define async query functions
    async def get_user_count():
        """Get total user count with simulated delay."""
        await asyncio.sleep(0.05)  # Simulate some processing time
        if isinstance(db, AsyncSession):
            result = await db.execute(select(func.count(User.id)))
            return result.scalar() or 0
        else:
            return db.query(User).count()

    async def get_recent_activity():
        """Get recent activity with simulated delay."""
        await asyncio.sleep(0.08)  # Simulate processing time
        cutoff_time = datetime.utcnow() - timedelta(days=7)

        if isinstance(db, AsyncSession):
            recent_users_result = await db.execute(
                select(func.count(User.id)).where(
                    User.created_at >= cutoff_time)
            )
            recent_posts_result = await db.execute(
                select(func.count(Post.id)).where(
                    Post.created_at >= cutoff_time)
            )
            return {
                "recent_users": recent_users_result.scalar() or 0,
                "recent_posts": recent_posts_result.scalar() or 0
            }
        else:
            recent_users = db.query(User).filter(
                User.created_at >= cutoff_time).count()
            recent_posts = db.query(Post).filter(
                Post.created_at >= cutoff_time).count()
            return {
                "recent_users": recent_users,
                "recent_posts": recent_posts
            }

    async def get_engagement_stats():
        """Get engagement statistics with simulated delay."""
        await asyncio.sleep(0.06)  # Simulate processing time

        if isinstance(db, AsyncSession):
            published_result = await db.execute(
                select(func.count(Post.id)).where(Post.published == True)
            )
            total_result = await db.execute(select(func.count(Post.id)))
            return {
                "published_posts": published_result.scalar() or 0,
                "total_posts": total_result.scalar() or 0
            }
        else:
            published = db.query(Post).filter(Post.published == True).count()
            total = db.query(Post).count()
            return {
                "published_posts": published,
                "total_posts": total
            }

    # Execute all queries concurrently
    user_count_task = asyncio.create_task(get_user_count())
    activity_task = asyncio.create_task(get_recent_activity())
    engagement_task = asyncio.create_task(get_engagement_stats())

    # Wait for all tasks to complete
    user_count, recent_activity, engagement_stats = await asyncio.gather(
        user_count_task, activity_task, engagement_task
    )

    end_time = datetime.utcnow()
    total_duration = (end_time - start_time).total_seconds()

    # Calculate engagement rate
    engagement_rate = 0.0
    if engagement_stats["total_posts"] > 0:
        engagement_rate = (
            engagement_stats["published_posts"] / engagement_stats["total_posts"]) * 100

    return {
        "message": "Async dashboard statistics generated successfully",
        "user": current_user,
        "async_stats": {
            "total_users": user_count,
            "recent_activity": recent_activity,
            "engagement": {
                **engagement_stats,
                "engagement_rate_percent": round(engagement_rate, 1)
            }
        },
        "performance": {
            "query_duration_seconds": total_duration,
            "concurrent_queries": 3,
            "start_time": start_time,
            "end_time": end_time
        },
        "environment": ENVIRONMENT,
        "note": "This endpoint demonstrates concurrent async database queries"
    }
