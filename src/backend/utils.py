# Database initialization utilities
from sqlalchemy.orm import Session
from models.models import User, Post


def init_sample_data(db: Session):
    """Initialize database with sample data (only if not already persisted)"""
    try:
        # Check if data already exists (from persistence)
        existing_users = db.query(User).count()
        existing_posts = db.query(Post).count()

        if existing_users > 0:
            print(
                f" Found {existing_users} users and {existing_posts} posts from persistent storage!")
            return {"loaded_from_persistence": True, "users": existing_users, "posts": existing_posts}

        print(" No existing data found - initializing fresh sample data...")

        # Create sample users
        users_data = [
            {"name": "Alice Johnson", "email": "alice@example.com",
                "age": 30, "bio": "Software engineer who loves FastAPI"},
            {"name": "Bob Smith", "email": "bob@example.com",
                "age": 25, "bio": "Data scientist exploring Pyodide"},
            {"name": "Charlie Brown", "email": "charlie@example.com",
                "age": 35, "bio": "Product manager building web apps"},
            {"name": "Diana Prince", "email": "diana@example.com",
                "age": 28, "bio": "UX designer passionate about user experience"},
            {"name": "Eve Wilson", "email": "eve@example.com",
                "age": 32, "bio": "DevOps engineer optimizing workflows"},
        ]

        created_users = []
        for user_data in users_data:
            user = User(**user_data)
            db.add(user)
            created_users.append(user)

        db.commit()

        # Refresh to get IDs
        for user in created_users:
            db.refresh(user)

        # Create sample posts
        posts_data = [
            {"title": "Welcome to Persistent FastAPI", "content": "This FastAPI demo now uses persistent storage! Data survives page reloads.",
                "author_id": created_users[0].id, "published": True},
            {"title": "SQLAlchemy + Pyodide Magic", "content": "Running SQLAlchemy with persistent databases entirely in the browser is amazing!",
                "author_id": created_users[1].id, "published": True},
            {"title": "Building Web Apps with No Backend", "content": "With persistent Pyodide, you can build full-stack apps that run entirely client-side.",
                "author_id": created_users[2].id, "published": False},
            {"title": "Data Science Meets Web Development", "content": "Pyodide bridges Python data science and web development beautifully.",
                "author_id": created_users[1].id, "published": True},
            {"title": "The Future of Client-Side Apps", "content": "Persistent storage in the browser opens up incredible possibilities.",
                "author_id": created_users[3].id, "published": True},
            {"title": "DevOps in the Browser", "content": "Managing persistent data without servers is a game-changer for deployment.",
                "author_id": created_users[4].id, "published": True},
            {"title": "Draft: More Ideas Coming", "content": "This is a draft post to show unpublished content.",
                "author_id": created_users[0].id, "published": False},
        ]

        for post_data in posts_data:
            post = Post(**post_data)
            db.add(post)

        db.commit()
        print(f" Created {len(users_data)} users and {len(posts_data)} posts")
        return {"loaded_from_persistence": False, "users": len(users_data), "posts": len(posts_data)}

    except Exception as e:
        db.rollback()
        print(f" Error initializing sample data: {e}")
        return {"error": str(e)}
