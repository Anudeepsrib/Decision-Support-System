"""
Application configuration settings.
Supports both Demo Mode and Production Mode via environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Demo Mode Configuration
    DEMO_MODE: bool = False
    
    # Demo User Configuration
    DEMO_USER_ID: str = "demo-admin"
    DEMO_USER_NAME: str = "Demo Admin"
    DEMO_USER_ROLE: str = "admin"
    
    # Demo Data Configuration
    DEMO_CASE_ID: str = "demo-case-001"
    DEMO_FINANCIAL_YEAR: str = "2024-25"
    DEMO_SBU_CODE: str = "SBU-D"
    
    # Database
    DATABASE_URL: str = "sqlite:///./kserc_demo.db"
    
    # Security
    SECRET_KEY: str = "demo-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # File Storage
    GENERATED_DOCS_PATH: str = "./generated_docs"
    UPLOAD_PATH: str = "./uploads"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def is_demo_mode() -> bool:
    """
    Global helper to check if system is running in DEMO MODE.
    
    Returns:
        True if DEMO_MODE is enabled, False otherwise.
    """
    return get_settings().DEMO_MODE


def get_demo_user() -> dict:
    """
    Get demo user information for auto-injection in demo mode.
    
    Returns:
        Dictionary containing demo user details.
    """
    settings = get_settings()
    return {
        "id": settings.DEMO_USER_ID,
        "username": settings.DEMO_USER_NAME,
        "role": settings.DEMO_USER_ROLE,
        "is_demo": True
    }
