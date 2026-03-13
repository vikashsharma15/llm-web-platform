from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class StoryJob(Base):
    __tablename__ = "story_jobs"

    id           = Column(Integer, primary_key=True, index=True)
    job_id       = Column(String, unique=True, index=True, nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # ← ownership
    theme        = Column(String, nullable=False)
    status       = Column(String, nullable=False, default="pending")  # pending|processing|completed|failed
    story_id     = Column(Integer, ForeignKey("stories.id"), nullable=True)
    error        = Column(String, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # session_id removed — user_id is the identity now
    # Relationships
    user  = relationship("User", back_populates="jobs")