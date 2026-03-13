from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base
import enum


class UserRole(str, enum.Enum):
    USER  = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String, unique=True, index=True, nullable=False)
    email      = Column(String, unique=True, index=True, nullable=False)
    password   = Column(String, nullable=False)
    role       = Column(
        SAEnum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.USER,
        nullable=False,
    )
    is_active  = Column(Boolean, default=False, nullable=False)  # ← False: email verify required
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    jobs    = relationship("StoryJob", back_populates="user", lazy="selectin")  
    stories = relationship("Story",    back_populates="user", lazy="selectin") 