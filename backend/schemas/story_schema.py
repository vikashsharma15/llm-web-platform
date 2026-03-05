from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class StoryOptionSchema(BaseModel):
    """Schema for a single story choice option."""
    text: str
    node_id: Optional[int] = None


class StoryNodeResponse(BaseModel):
    """Response schema for a single story node with its options."""
    id: int
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False
    options: List[StoryOptionSchema] = []

    model_config = {"from_attributes": True}


class CreateStoryRequest(BaseModel):
    """
    Request schema for creating a story.
    Pointer #3 — Pydantic validates input before it reaches the controller.
    Pointer #9 — validation errors caught by validation_middleware → consistent error format.
    """
    theme: str

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Rejects empty, whitespace-only, or too short themes."""
        if not v.strip():
            raise ValueError("Theme cannot be empty or whitespace")
        if len(v.strip()) < 3:
            raise ValueError("Theme must be at least 3 characters long")
        return v.strip()


class StoryResponse(BaseModel):
    """Response schema for a complete story with all nodes."""
    id: int
    title: str
    session_id: Optional[str] = None
    created_at: datetime
    root_node: StoryNodeResponse
    all_nodes: Dict[int, StoryNodeResponse]

    model_config = {"from_attributes": True}