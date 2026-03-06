from typing import List, Dict, Optional
from datetime import datetime
import re
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
        """Validates theme — rejects empty, too short, too long, gibberish."""
        v = v.strip()

        if not v:
            raise ValueError("Theme cannot be empty or whitespace")
        if len(v) < 3:
            raise ValueError("Theme must be at least 3 characters long")
        if len(v) > 30:
            raise ValueError("Theme must be at most 30 characters long")
        if not re.match(r'^[a-zA-Z0-9\s]+$', v):
            raise ValueError("Theme must contain only letters, numbers and spaces")

        words = v.split()
        if len(words) > 3:
            raise ValueError("Theme must be at most 3 words")
        for word in words:
            if len(word) > 12:
                raise ValueError("Each word must be at most 12 characters")
        if len(words) != len(set(w.lower() for w in words)):
            raise ValueError("Theme must not contain duplicate words")
        if re.search(r'(.{2,})\1+', v.replace(' ', '').lower()):
            raise ValueError("Theme looks like gibberish — please enter a valid theme")
        if re.search(r'(.)\1{3,}', v):
            raise ValueError("Theme looks like gibberish — please enter a valid theme")
        if not re.search(r'[aeiouAEIOU]', v):
            raise ValueError("Theme must contain at least one vowel")

        return v


class StoryResponse(BaseModel):
    """
    Response schema for a complete story.
    - session_id excluded — internal field, not exposed to client
    - root_node excluded from all_nodes — no duplicate data
    """
    id: int
    title: str
    created_at: datetime
    root_node: StoryNodeResponse
    # all_nodes excludes root — client uses root_node separately
    nodes: Dict[int, StoryNodeResponse]

    model_config = {"from_attributes": True}