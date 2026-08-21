"""
Async database connection and session management.
Uses SQLAlchemy 2.0 async API with asyncpg driver.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base

from app.config import settings


def create_database_engine():
    """Create an engine with options supported by the configured database.

    PostgreSQL/asyncpg uses SQLAlchemy's normal async queue pool. SQLite does
    not accept those pool sizing parameters, so it uses only common options.
    Alembic owns its short-lived NullPool separately in ``alembic/env.py``.
    """
    database_url = make_url(settings.DATABASE_URL)
    options = {"echo": settings.DEBUG, "pool_pre_ping": True}
    if database_url.get_backend_name() != "sqlite":
        options.update(
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        )
    return create_async_engine(database_url, **options)


engine = create_database_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    Ensures session is properly closed after request.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    Should be called on application startup.
    """
    # Schema changes are owned by Alembic. Startup only verifies connectivity.
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))


async def close_db() -> None:
    """
    Close database connections.
    Should be called on application shutdown.
    """
    await engine.dispose()
