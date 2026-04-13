"""Cấu hình Ứng dụng sử dụng Cài đặt Pydantic"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cài đặt ứng dụng được tải từ các biến môi trường"""
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore"
    )
    
    # Cấu hình Cơ sở dữ liệu
    BACKEND_DB_HOST: str = Field(default="postgres_application_db")
    BACKEND_DB_PORT: int = Field(default=5432)
    BACKEND_DB_NAME: str = Field(default="sme_pulse_oltp")
    BACKEND_DB_USER: str = Field(default="postgres")
    BACKEND_DB_PASSWORD: str = Field(default="postgres")
    BACKEND_POOL_SIZE: int = Field(default=20)
    BACKEND_MAX_OVERFLOW: int = Field(default=10)
    
    # Bảo mật
    BACKEND_SECRET_KEY: str = Field(default="change-me")
    BACKEND_ALGORITHM: str = Field(default="HS256")
    BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # CORS (sẽ được phân tích cú pháp từ chuỗi phân tách bằng dấu phẩy)
    BACKEND_ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:3001")
    
    # Môi trường
    BACKEND_ENVIRONMENT: str = Field(default="development")
    BACKEND_DEBUG: bool = Field(default=True)
    BACKEND_LOG_LEVEL: str = Field(default="INFO")
    
    # Ghi nhật ký
    BACKEND_LOG_FORMAT: str = Field(default="json")
    BACKEND_LOG_FILE: str = Field(default="logs/backend.log")
    
    # Giới hạn tốc độ
    BACKEND_RATE_LIMIT_ENABLED: bool = Field(default=True)
    BACKEND_RATE_LIMIT_REQUESTS: int = Field(default=5)
    BACKEND_RATE_LIMIT_WINDOW: int = Field(default=60)
    
    # Redis & Celery
    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/0")

    # Trino (Lakehouse analytics)
    TRINO_HOST: str = Field(default="trino")
    TRINO_PORT: int = Field(default=8080)
    TRINO_USER: str = Field(default="api_backend")
    TRINO_CATALOG: str = Field(default="sme_lake")
    TRINO_SCHEMA: str = Field(default="gold")
    TRINO_TIMEOUT: int = Field(default=40)

    # ML runtime
    MLFLOW_TRACKING_URI: str = Field(default="file:///opt/airflow/mlflow")
    
    # MinIO
    MINIO_ENDPOINT: str = Field(default="minio:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="sme-lake")
    MINIO_SECURE: bool = Field(default=False)
    
    # Nhúng Metabase
    METABASE_SITE_URL: str = Field(default="http://localhost:3000")
    METABASE_EMBEDDING_SECRET_KEY: str = Field(default="change-me-metabase-secret")
    METABASE_TOKEN_EXPIRE_SECONDS: int = Field(default=600)
    
    # Xuất Excel
    EXPORT_TEMP_DIR: str = Field(default="/tmp/exports")
    
    def get_cors_origins(self) -> List[str]:
        """Phân tích các nguồn CORS từ chuỗi phân tách bằng dấu phẩy"""
        return [origin.strip() for origin in self.BACKEND_ALLOWED_ORIGINS.split(",")]

    def is_development(self) -> bool:
        """Xác định môi trường local/dev để cho phép một số mặc định thuận tiện."""
        return self.BACKEND_ENVIRONMENT.lower() in {"dev", "development", "local"}

    def validate_security_settings(self) -> None:
        """Fail fast ở non-dev nếu secret quan trọng vẫn đang dùng giá trị mặc định."""
        weak_values = {"", "change-me", "secret", "default", "changeme"}
        weak_fields = []

        if self.BACKEND_SECRET_KEY.lower() in weak_values:
            weak_fields.append("BACKEND_SECRET_KEY")

        if self.METABASE_EMBEDDING_SECRET_KEY.lower() in weak_values:
            weak_fields.append("METABASE_EMBEDDING_SECRET_KEY")

        if weak_fields and not self.is_development():
            raise ValueError(
                "Insecure runtime configuration for non-development environment: "
                + ", ".join(weak_fields)
            )

    def runtime_summary(self) -> dict:
        """Trả về snapshot cấu hình đã làm sạch để log khi startup."""
        return {
            "environment": self.BACKEND_ENVIRONMENT,
            "debug": self.BACKEND_DEBUG,
            "log_level": self.BACKEND_LOG_LEVEL,
            "rate_limit_enabled": self.BACKEND_RATE_LIMIT_ENABLED,
            "db_host": self.BACKEND_DB_HOST,
            "db_name": self.BACKEND_DB_NAME,
            "redis_host": self.REDIS_HOST,
            "trino_host": self.TRINO_HOST,
            "trino_port": self.TRINO_PORT,
            "trino_catalog": self.TRINO_CATALOG,
            "trino_schema": self.TRINO_SCHEMA,
            "mlflow_tracking_uri": self.MLFLOW_TRACKING_URI,
            "secret_key_is_default": self.BACKEND_SECRET_KEY.lower() in {"", "change-me", "secret", "default", "changeme"},
            "metabase_secret_is_default": self.METABASE_EMBEDDING_SECRET_KEY.lower() in {"", "change-me", "secret", "default", "changeme"},
        }
    
    @property
    def DATABASE_URL(self) -> str:
        """Xây dựng URL cơ sở dữ liệu bất đồng bộ cho asyncpg"""
        return (
            f"postgresql+asyncpg://{self.BACKEND_DB_USER}:{self.BACKEND_DB_PASSWORD}"
            f"@{self.BACKEND_DB_HOST}:{self.BACKEND_DB_PORT}/{self.BACKEND_DB_NAME}"
        )
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Xây dựng URL cơ sở dữ liệu đồng bộ cho Alembic"""
        return (
            f"postgresql://{self.BACKEND_DB_USER}:{self.BACKEND_DB_PASSWORD}"
            f"@{self.BACKEND_DB_HOST}:{self.BACKEND_DB_PORT}/{self.BACKEND_DB_NAME}"
        )


settings = Settings()
