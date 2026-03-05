from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class StoryJobCreate(BaseModel):
    theme: str

    @field_validator("theme")
    @classmethod
    def theme_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Theme cannot be empty or whitespace")
        return v.strip()


class StoryJobResponse(BaseModel):
    job_id: str
    theme: str
    status: str
    story_id: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}