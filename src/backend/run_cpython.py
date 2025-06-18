"""
Standalone runner for the FastAPI application using uvicorn.
Use this to run the backend with CPython for testing.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "app_main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
