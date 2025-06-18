"""
Enhanced Bridge FastAPI Demo - Compatibility Wrapper

This file maintains backward compatibility with the existing frontend
while using the new modular backend structure.

The EXACT same API endpoints are available, just organized better!
"""

# Import the new modular app
import sys
import os

# Add the app directory to Python path for imports
# In Pyodide, __file__ is not available, so we use the working directory
if 'pyodide' in sys.modules or '/persist/api' in os.getcwd():
    # We're in Pyodide, working directory is already /persist/api
    app_dir = os.path.join(os.getcwd(), "app")
else:
    # We're in regular Python
    app_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, app_dir)

try:    # Import from the new app structure
    from app.app_main import app
    from app.core.runtime import IS_PYODIDE
    from core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("✅ Successfully loaded modular FastAPI app")

    # Re-export the app for compatibility
    __all__ = ["app"]

except ImportError as e:
    print(f"❌ Failed to import modular app: {e}")
    
    # Set fallback values
    IS_PYODIDE = 'pyodide' in sys.modules

    # Fallback: Create a minimal app if imports fail
    from fastapi import FastAPI

    app = FastAPI(
        title="Enhanced Bridge SQLAlchemy Demo (Fallback)",
        description="Fallback app - modular imports failed",
        version="2.0.0"
    )

    @app.get("/")
    def fallback_root():
        return {
            "error": "Modular app import failed",
            "message": "Using fallback app",
            "suggestion": "Check if all dependencies are installed"
        }

# For uvicorn compatibility
if __name__ == "__main__":
    if not IS_PYODIDE:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
