import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


# Async engine — DATABASE_URL must use async driver
# SQLite:     sqlite+aiosqlite:///./database.db
# PostgreSQL: postgresql+asyncpg://user:pass@host/db
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # auto-reconnect on stale connections
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoid lazy load errors after commit
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency — provides async DB session per request.
    Rolls back on error, always closes session.
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except SQLAlchemyError as e:
            logger.error(f"DB session error: {e}")
            await db.rollback()
            raise


async def create_tables() -> None:
    """Creates all tables on app startup — runs once via main.py."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create tables: {e}")
        raise