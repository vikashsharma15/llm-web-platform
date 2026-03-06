from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


class Story(Base):
    """Represents a generated story — parent of all story nodes."""

    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)                     # LLM generated story title
    theme = Column(String, index=True)                     # used for cache lookup 
    session_id = Column(String, index=True)                # links story to user session
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    nodes = relationship("StoryNode", back_populates="story")


class StoryNode(Base):
    """Represents a single node in the story tree — content + choices."""

    __tablename__ = "story_nodes"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    content = Column(String)                              
    is_root = Column(Boolean, default=False)               
    is_ending = Column(Boolean, default=False)            
    is_winning_ending = Column(Boolean, default=False)     
    options = Column(JSON, default=list)                  

    story = relationship("Story", back_populates="nodes")