"""Simple test FastAPI app."""
from fastapi import FastAPI


def create_test_app():
    """Create a simple test app."""
    app = FastAPI(title="Test App")

    @app.get("/", operation_id="root")
    def root():
        return {"message": "Test app works!"}

    return app


app = create_test_app()
