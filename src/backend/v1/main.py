# Enhanced Bridge FastAPI Demo with SQLAlchemy Support & Persistence
"""
This demo showcases the Enhanced Pyodide FastAPI Bridge with automatic SQLAlchemy serialization
and persistent storage. The EXACT same code works identically in both backend and Pyodide environments!

Key Features Demonstrated:
- Direct return of SQLAlchemy model instances (automatic JSON serialization)
- Full dependency injection with Depends()
- Standard FastAPI patterns (no bridge-specific code)
- Complex responses with mixed SQLAlchemy models
- uvicorn.run() compatibility
- PERSISTENT STORAGE - data survives page reloads using IndexedDB!
- Zero code changes between backend and Pyodide

Persistence Features:
- SQLite database stored in IndexedDB (survives browser restarts)
- Automatic detection of existing data vs fresh initialization
- Database file persistence with size monitoring
- Full ACID compliance with persistent transactions

Note: FastAPI, Pydantic, and SQLAlchemy are automatically installed by the bridge!
"""

from database.connection import SessionLocal
from datetime import datetime, timedelta
from typing import List, Optional
import sys

# === STANDARD FASTAPI IMPORTS (unchanged from backend!) ===
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import uvicorn

# === SQLALCHEMY IMPORTS ===
from sqlalchemy.orm import Session
from sqlalchemy import func

# === LOCAL IMPORTS ===
from database.connection import get_db, create_tables, DATABASE_URL, ENVIRONMENT
from models.models import User, Post
from schemas.schemas import UserCreate, UserUpdate, PostCreate, PostUpdate
from utils import init_sample_data

# === FASTAPI APP CREATION (works identically in backend and Pyodide!) ===
app = FastAPI(
    title="Enhanced Bridge SQLAlchemy Demo",
    description="Demonstrates automatic SQLAlchemy model serialization with zero code changes",
    version="2.0.0",
    openapi_tags=[
        {"name": "users", "description": "User management with SQLAlchemy models"},
        {"name": "posts", "description": "Blog posts with relationships"},
        {"name": "dashboard", "description": "Complex responses with mixed models"},
        {"name": "system", "description": "System information and diagnostics"},
    ]
)

# Create tables
create_tables()


def get_current_user():
    """Simulated authentication dependency with environment detection"""
    environment_info = {
        "pyodide-persistent": "Pyodide Browser (Persistent)",
        "fastapi-production": "FastAPI Backend (Production)",
        "fastapi-development": "FastAPI Backend (Development)"
    }

    return {
        "id": 1,
        "name": "Demo User",
        "role": "admin",
        "environment": environment_info.get(ENVIRONMENT, "Unknown Environment"),
        "database_type": ENVIRONMENT
    }


# Initialize database on startup
startup_db = SessionLocal()
init_result = None
try:
    init_result = init_sample_data(startup_db)
finally:
    startup_db.close()

print(" Enhanced Bridge database initialization complete!")
if init_result:
    if init_result.get("loaded_from_persistence"):
        print(
            f" Persistence Status:  ACTIVE - Loaded {init_result['users']} users and {init_result['posts']} posts from storage")
    elif init_result.get("error"):
        print(f" Persistence Status:  ERROR - {init_result['error']}")
    else:
        print(
            f" Persistence Status:  FRESH - Created {init_result['users']} users and {init_result['posts']} posts")

# === API ENDPOINTS DEMONSTRATING SQLALCHEMY SERIALIZATION ===


@app.get("/",
         summary="Welcome to Enhanced Bridge Demo",
         tags=["system"])
def read_root(current_user: dict = Depends(get_current_user)):
    """Welcome endpoint showcasing dependency injection and persistence info"""

    # Check if we're using persistent storage
    is_persistent = "persist" in DATABASE_URL

    return {
        "message": f"Welcome {current_user['name']} to Enhanced SQLAlchemy Bridge Demo!",
        "environment": current_user["environment"],
        "persistence": {
            "enabled": is_persistent,
            "database_url": DATABASE_URL,
            "status": " Data survives page reloads!" if is_persistent else " Using in-memory database",
            "note": "Try refreshing the page - your data will still be here!" if is_persistent else "Data will reset when you refresh the page"
        },
        "features": [
            " Direct SQLAlchemy model returns",
            " Automatic JSON serialization",
            " Full dependency injection",
            " Standard FastAPI patterns",
            " Zero code changes needed",
            " Persistent storage (survives reloads)" if is_persistent else " In-memory storage (resets on reload)"
        ],
        "endpoints": {
            "users": "/users - Get all users (SQLAlchemy list)",
            "user": "/users/1 - Get single user (SQLAlchemy model)",
            "posts": "/posts - Get all posts (with relationships)",
            "dashboard": "/dashboard - Complex mixed response",
            "persistence": "/persistence/status - Detailed persistence information",
            "docs": "/docs - Interactive API documentation"
        }
    }

# === USER ENDPOINTS (Direct SQLAlchemy Model Returns) ===


@app.get("/users",
         summary="Get all users",
         description="Returns list of SQLAlchemy User models - automatic serialization!",
         tags=["users"])
def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of users to return"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all users - direct return of SQLAlchemy model list"""
    print(
        f"User {current_user['name']} requesting users (skip={skip}, limit={limit})")

    users = db.query(User).offset(skip).limit(limit).all()

    # Direct return of SQLAlchemy models - enhanced bridge handles serialization!
    return users


@app.get("/users/{user_id}",
         summary="Get user by ID",
         description="Returns single SQLAlchemy User model - automatic serialization!",
         tags=["users"])
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get single user by ID - direct SQLAlchemy model return"""
    print(f"User {current_user['name']} requesting user {user_id}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found")

    # Direct return of SQLAlchemy model - automatic serialization!
    return user


@app.post("/users",
          summary="Create new user",
          description="Creates and returns new SQLAlchemy User model",
          tags=["users"],
          status_code=201)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create new user - returns SQLAlchemy model directly"""
    print(f"User {current_user['name']} creating new user: {user_data.name}")

    # Check for existing email
    existing_user = db.query(User).filter(
        User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        age=user_data.age,
        bio=user_data.bio
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    #  AUTOMATIC PERSISTENCE: Since this is a POST endpoint, the Pyodide engine
    # will automatically call FS.syncfs() to save the database to IndexedDB!
    # No additional code needed - persistence happens automatically.
    #
    # Optional manual save (though automatic save will also happen):
    # save_persistent_state()

    # Direct return of new SQLAlchemy model!
    return db_user


@app.put("/users/{user_id}",
         summary="Update user",
         description="Updates and returns SQLAlchemy User model",
         tags=["users"])
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update user - returns updated SQLAlchemy model"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found")

    # Update fields - compatible with both Pydantic v1 and v2
    try:
        # Pydantic v2 method
        update_data = user_data.model_dump(exclude_unset=True)
    except AttributeError:
        # Pydantic v1 method
        update_data = user_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # Direct return of updated SQLAlchemy model!
    return user


@app.delete("/users/{user_id}",
            summary="Delete user",
            tags=["users"])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete user and return confirmation"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found")

    user_name = user.name
    db.delete(user)
    db.commit()

    return {"message": f"User {user_name} (ID: {user_id}) deleted successfully"}

# === POST ENDPOINTS (SQLAlchemy Models with Relationships) ===


@app.get("/posts",
         summary="Get all posts",
         description="Returns list of SQLAlchemy Post models with relationships",
         tags=["posts"])
def get_all_posts(
    published_only: bool = Query(
        False, description="Filter to published posts only"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all posts - SQLAlchemy models with relationships"""
    query = db.query(Post)
    if published_only:
        query = query.filter(Post.published == True)

    posts = query.all()

    # Direct return of SQLAlchemy models with relationships!
    return posts


@app.get("/posts/{post_id}",
         summary="Get post by ID",
         description="Returns single SQLAlchemy Post model with author relationship",
         tags=["posts"])
def get_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Get single post by ID with author relationship"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=404, detail=f"Post {post_id} not found")

    # Direct return includes relationship data!
    return post


@app.post("/posts",
          summary="Create new post",
          description="Creates and returns new SQLAlchemy Post model",
          tags=["posts"],
          status_code=201)
def create_post(
    post_data: PostCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create new post"""
    # Verify author exists
    author = db.query(User).filter(User.id == post_data.author_id).first()
    if not author:
        raise HTTPException(
            status_code=400, detail=f"Author {post_data.author_id} not found")

    db_post = Post(
        title=post_data.title,
        content=post_data.content,
        published=post_data.published,
        author_id=post_data.author_id
    )

    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    # Direct return of new SQLAlchemy model!
    return db_post


@app.get("/users/{user_id}/posts",
         summary="Get user's posts",
         description="Returns list of posts by specific user",
         tags=["posts"])
def get_user_posts(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all posts by a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found")

    posts = db.query(Post).filter(Post.author_id == user_id).all()

    # Direct return of SQLAlchemy model list!
    return posts

# === COMPLEX DASHBOARD ENDPOINTS ===


@app.get("/dashboard",
         summary="Dashboard with mixed SQLAlchemy models",
         description="Complex response combining multiple SQLAlchemy models",
         tags=["dashboard"])
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Dashboard with complex mixed SQLAlchemy model response"""

    # Get recent users and posts
    recent_users = db.query(User).order_by(
        User.created_at.desc()).limit(3).all()
    recent_posts = db.query(Post).filter(Post.published == True).order_by(
        Post.created_at.desc()).limit(5).all()

    # Get statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_posts = db.query(Post).count()
    published_posts = db.query(Post).filter(Post.published == True).count()

    # Return complex structure with SQLAlchemy models
    return {
        "user_info": current_user,
        "recent_users": recent_users,           # List of SQLAlchemy User models
        "recent_posts": recent_posts,           # List of SQLAlchemy Post models
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


@app.get("/analytics",
         summary="Analytics with aggregated data",
         description="Complex analytics combining SQLAlchemy queries and models",
         tags=["dashboard"])
def get_analytics(
    db: Session = Depends(get_db)
):
    """Analytics endpoint with SQLAlchemy aggregations and model returns"""

    # Users by age group
    young_users = db.query(User).filter(User.age < 30).all()
    middle_users = db.query(User).filter(User.age >= 30, User.age < 50).all()
    senior_users = db.query(User).filter(User.age >= 50).all()

    # Most active authors
    active_authors = db.query(User).join(Post).group_by(
        User.id).order_by(func.count(Post.id).desc()).limit(3).all()

    return {
        "user_demographics": {
            "young_users": young_users,      # SQLAlchemy models
            "middle_users": middle_users,    # SQLAlchemy models
            "senior_users": senior_users,    # SQLAlchemy models
        },
        "top_authors": active_authors,       # SQLAlchemy models
        "summary": {
            "total_analyzed": len(young_users) + len(middle_users) + len(senior_users),
            "most_common_age_group": "young" if len(young_users) > max(len(middle_users), len(senior_users)) else "middle" if len(middle_users) > len(senior_users) else "senior",
            "analysis_timestamp": datetime.utcnow()
        }
    }

# === SYSTEM INFORMATION ===


@app.get("/system/info",
         summary="System information",
         description="Get system and runtime information",
         tags=["system"])
def get_system_info(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """System information endpoint"""

    # Get database statistics
    db_stats = {
        "total_users": db.query(User).count(),
        "total_posts": db.query(Post).count(),
        "active_users": db.query(User).filter(User.is_active == True).count(),
        "published_posts": db.query(Post).filter(Post.published == True).count()
    }

    # Check persistence status
    is_persistent = "persist" in DATABASE_URL

    return {
        "status": " Enhanced Bridge Active",
        "environment": {
            "type": current_user["environment"],
            "database_type": ENVIRONMENT,
            "is_pyodide": hasattr(sys, '_pyodide_core'),
            "is_persistent": "persist" in DATABASE_URL,
            "supports_uvicorn": ENVIRONMENT.startswith("fastapi")
        },
        "persistence": {
            "enabled": "persist" in DATABASE_URL,
            "database_url": DATABASE_URL,
            "type": {
                "pyodide-persistent": "IndexedDB-backed SQLite",
                "fastapi-production": "Production Database",
                "fastapi-development": "In-Memory SQLite"
            }.get(ENVIRONMENT, "Unknown")
        },
        "features": {
            "sqlalchemy_serialization": " Automatic",
            "dependency_injection": " Full Support",
            "fastapi_patterns": " Standard",
            "uvicorn_compatibility": " Full Support" if ENVIRONMENT.startswith("fastapi") else " No-op stub",
            "data_persistence": " Enabled" if "persist" in DATABASE_URL else " Disabled"
        },
        "database": db_stats,
        "runtime": {
            "python_version": sys.version,
            "is_pyodide": hasattr(sys, '_pyodide_core'),
            "environment_detected": ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


@app.get("/persistence/status",
         summary="Detailed persistence information",
         description="Get comprehensive information about data persistence",
         tags=["system"])
def get_persistence_status(
    db: Session = Depends(get_db)
):
    """Detailed persistence status and database information"""
    import os

    # Check if we're using persistent storage
    is_persistent = "persist" in DATABASE_URL

    # Get database file info if persistent
    db_file_info = None
    if is_persistent:
        try:
            # Extract path from URL
            db_path = DATABASE_URL.replace("sqlite:///", "")
            if os.path.exists(db_path):
                stat = os.stat(db_path)
                db_file_info = {
                    "path": db_path,
                    "size_bytes": stat.st_size,
                    "size_human": f"{stat.st_size / 1024:.2f} KB" if stat.st_size > 0 else "0 KB",
                    "exists": True
                }
            else:
                db_file_info = {
                    "path": db_path,
                    "exists": False,
                    "note": "Database file will be created on first write"
                }
        except Exception as e:
            db_file_info = {"error": str(e)}

    # Get comprehensive database statistics
    users = db.query(User).all()
    posts = db.query(Post).all()

    # Calculate some analytics
    recent_users = [u for u in users if (
        datetime.utcnow() - u.created_at).days < 7]
    recent_posts = [p for p in posts if (
        datetime.utcnow() - p.created_at).days < 7]

    return {
        "persistence": {
            "enabled": is_persistent,
            "type": "IndexedDB-backed SQLite" if is_persistent else "In-Memory SQLite",
            "database_url": DATABASE_URL,
            "survives_reload": is_persistent,
            "storage_backend": "IDBFS (IndexedDB)" if is_persistent else "Memory"
        },
        "database_file": db_file_info,
        "data_summary": {
            "total_users": len(users),
            "total_posts": len(posts),
            "recent_users_7d": len(recent_users),
            "recent_posts_7d": len(recent_posts),
            "published_posts": len([p for p in posts if p.published]),
            "active_users": len([u for u in users if u.is_active])
        },
        "sample_data": {
            "latest_user": users[-1].name if users else None,
            "latest_post": posts[-1].title if posts else None,
            "oldest_user": users[0].name if users else None,
            "oldest_post": posts[0].title if posts else None
        },
        "recommendations": [
            " Data is persistent - safe to refresh page" if is_persistent else " Data will reset on page refresh",
            " Try creating new users/posts and refreshing to test persistence" if is_persistent else " Load this demo with persistence enabled for data to survive reloads",
            " Use /dashboard for comprehensive data visualization",
            " Check /users and /posts endpoints for SQLAlchemy model returns"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


# === STANDARD UVICORN RUN (works in backend, stubbed in Pyodide!) ===
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
