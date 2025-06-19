"""Application settings and configuration."""
import os
from typing import Optional, List
from pydantic import BaseModel, Field

from .runtime import get_environment, IS_PYODIDE


class Settings(BaseModel):
    """Application settings with environment-specific defaults."""

    # Application
    app_name: str = Field(default="Enhanced Bridge SQLAlchemy Demo")
    app_version: str = Field(default="2.0.0")
    app_description: str = Field(
        default="Demonstrates automatic SQLAlchemy model serialization with zero code changes"
    )
    # Environment
    environment: str = Field(default_factory=get_environment)
    debug: bool = Field(default=False)

    # Database
    database_url: Optional[str] = Field(default=None)

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "*"] if IS_PYODIDE else ["http://localhost:3000", "http://localhost:5173"]
    )

    # API
    api_v1_prefix: str = Field(default="/api/v1")
    openapi_url: str = Field(default="/openapi.json")
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


# Global settings instance
settings = get_settings()
