"""Quản lý AsyncSession của SQLAlchemy"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


# Tạo async engine
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.BACKEND_POOL_SIZE,
    max_overflow=settings.BACKEND_MAX_OVERFLOW,
    pool_pre_ping=True,
    poolclass=NullPool if settings.BACKEND_ENVIRONMENT == "test" else None,
)

# Tạo async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency cho FastAPI routes để lấy session cơ sở dữ liệu"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
