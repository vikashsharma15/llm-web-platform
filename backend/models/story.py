from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


class Story(Base):
    __tablename__ = "stories"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # ← ADD THIS
    title      = Column(String, nullable=False)
    theme      = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # session_id — REMOVE THIS LINE if it's still there

    nodes = relationship("StoryNode", back_populates="story", lazy="selectin")
    user  = relationship("User", back_populates="stories")


class StoryNode(Base):
    __tablename__ = "story_nodes"

    id                = Column(Integer, primary_key=True, index=True)
    story_id          = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    content           = Column(String, nullable=False)
    is_root           = Column(Boolean, default=False, nullable=False)
    is_ending         = Column(Boolean, default=False, nullable=False)
    is_winning_ending = Column(Boolean, default=False, nullable=False)
    options           = Column(JSON, default=list, nullable=False)

    story = relationship("Story", back_populates="nodes")