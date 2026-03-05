from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import get_settings

# Database Engine
engine = create_engine(get_settings().DATABASE_URL)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for all models
class Base(DeclarativeBase):
    pass


# Dependency injection for DB session (used in controllers)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Creates all tables on startup (called from main.py)
def create_tables():
    Base.metadata.create_all(bind=engine)