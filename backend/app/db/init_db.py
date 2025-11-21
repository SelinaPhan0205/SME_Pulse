"""Database Schema Initialization"""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import engine

logger = logging.getLogger(__name__)

REQUIRED_SCHEMAS = ["core", "finance", "analytics"]


async def create_schemas_if_not_exists(db_engine: AsyncEngine) -> None:
    """Create PostgreSQL schemas if they dont exist"""
    async with db_engine.begin() as conn:
        for schema in REQUIRED_SCHEMAS:
            try:
                await conn.execute(
                    text(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                )
                logger.info(f"Schema {schema} ensured")
            except Exception as e:
                logger.error(f"Failed to create schema {schema}: {e}")
                raise


async def initialize_database_schemas() -> None:
    """Application startup hook to initialize database schemas"""
    logger.info("Initializing database schemas...")
    await create_schemas_if_not_exists(engine)
    logger.info("Database schemas initialized successfully")
