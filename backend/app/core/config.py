"""Application Configuration using Pydantic Settings"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    BACKEND_DB_HOST: str = Field(default="postgres_application_db")
    BACKEND_DB_PORT: int = Field(default=5432)
    BACKEND_DB_NAME: str = Field(default="sme_pulse_oltp")
    BACKEND_DB_USER: str = Field(default="postgres")
    BACKEND_DB_PASSWORD: str = Field(default="postgres")
    BACKEND_POOL_SIZE: int = Field(default=20)
    BACKEND_MAX_OVERFLOW: int = Field(default=10)
    
    # Security
    BACKEND_SECRET_KEY: str = Field(default="change-me")
    BACKEND_ALGORITHM: str = Field(default="HS256")
    BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # CORS (will be parsed from comma-separated string)
    BACKEND_ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")
    
    # Environment
    BACKEND_ENVIRONMENT: str = Field(default="development")
    BACKEND_DEBUG: bool = Field(default=True)
    BACKEND_LOG_LEVEL: str = Field(default="INFO")
    
    # Logging
    BACKEND_LOG_FORMAT: str = Field(default="json")
    BACKEND_LOG_FILE: str = Field(default="logs/backend.log")
    
    # Rate Limiting
    BACKEND_RATE_LIMIT_ENABLED: bool = Field(default=True)
    BACKEND_RATE_LIMIT_REQUESTS: int = Field(default=5)
    BACKEND_RATE_LIMIT_WINDOW: int = Field(default=60)
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.BACKEND_ALLOWED_ORIGINS.split(",")]
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL for asyncpg"""
        return (
            f"postgresql+asyncpg://{self.BACKEND_DB_USER}:{self.BACKEND_DB_PASSWORD}"
            f"@{self.BACKEND_DB_HOST}:{self.BACKEND_DB_PORT}/{self.BACKEND_DB_NAME}"
        )
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL for Alembic"""
        return (
            f"postgresql://{self.BACKEND_DB_USER}:{self.BACKEND_DB_PASSWORD}"
            f"@{self.BACKEND_DB_HOST}:{self.BACKEND_DB_PORT}/{self.BACKEND_DB_NAME}"
        )


settings = Settings()
