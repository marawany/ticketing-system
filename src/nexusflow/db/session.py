"""
Database Session Management

Async SQLAlchemy session handling for PostgreSQL persistent storage.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from nexusflow.config import settings
from nexusflow.db.models import Base

logger = structlog.get_logger(__name__)

# Create async engine
_engine = None
_session_factory = None


def get_database_url() -> str:
    """Get the database URL."""
    return settings.database_url


async def init_db() -> None:
    """Initialize the database, creating tables if they don't exist."""
    global _engine, _session_factory

    database_url = get_database_url()
    
    # PostgreSQL-optimized settings
    engine_kwargs = {
        "echo": settings.debug,
        "future": True,
        "pool_pre_ping": True,  # Verify connections before using
        "pool_size": 10,
        "max_overflow": 20,
    }

    _engine = create_async_engine(database_url, **engine_kwargs)

    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mask credentials in log
    log_url = database_url.split("@")[-1] if "@" in database_url else database_url
    logger.info("Database initialized", url=f"postgresql://...@{log_url}")


async def close_db() -> None:
    """Close the database connection."""
    global _engine

    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection closed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    global _session_factory

    if _session_factory is None:
        await init_db()

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get a database session."""
    async with get_session() as session:
        yield session
