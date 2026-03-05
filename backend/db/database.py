import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Engine created from DATABASE_URL in .env — never hardcoded
engine = create_engine(settings.DATABASE_URL)

# Session factory — autocommit off, manual commit required
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """
    FastAPI dependency — provides DB session per request.
    Pointer #6 — rolls back on error, always closes session.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"DB session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """Creates all tables on app startup — runs once via main.py."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create tables: {e}")
        raise