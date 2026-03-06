from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class StoryJobResponse(BaseModel):
    """
    Response schema for story job status.
    consistent response format across all endpoints.
    Note: StoryJobCreate removed — CreateStoryRequest in story.py handles input validation.
    """

    job_id: str
    theme: str
    status: str                          # pending → processing → completed/failed
    story_id: Optional[int] = None       # set once story generation completes
    error: Optional[str] = None          # populated if job fails
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Allows direct mapping from SQLAlchemy StoryJob model
    model_config = {"from_attributes": True}