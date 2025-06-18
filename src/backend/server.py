"""Server entry point for the FastAPI backend."""
from app_main import app
import sys
import os

# Add the app directory to Python path
app_dir = os.path.join(os.path.dirname(__file__), "app")
sys.path.insert(0, app_dir)

# Import the app

# Make it available for uvicorn
__all__ = ["app"]
