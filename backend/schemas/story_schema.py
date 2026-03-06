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
    Pointer #9 — validation errors caught by validation_middleware.
    """
    theme: str

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """
        Validates theme — rejects gibberish before wasting an LLM call.
        Allows minor typos (aapplee, spce) — LLM will auto-correct these.
        """
        # Empty check before strip — catches ""
        if not v:
            raise ValueError("Theme cannot be empty")

        # Whitespace only check — catches "   "
        if not v.strip():
            raise ValueError("Theme cannot be whitespace only")

        v = v.strip()
        clean = v.replace(" ", "").lower()

        if len(v) < 3:
            raise ValueError("Theme must be at least 3 characters long")
        if len(v) > 30:
            raise ValueError("Theme must be at most 30 characters long")

        # Only letters, numbers and spaces
        if not re.match(r'^[a-zA-Z0-9\s]+$', v):
            raise ValueError("Theme must contain only letters, numbers and spaces")

        words = v.split()

        # Max 3 words
        if len(words) > 3:
            raise ValueError("Theme must be at most 3 words")

        # Each word max 12 chars — catches "bikecyclebikecykle"
        for word in words:
            if len(word) > 12:
                raise ValueError("Each word must be at most 12 characters")

        # No duplicate words — catches "space space"
        if len(words) != len(set(w.lower() for w in words)):
            raise ValueError("Theme must not contain duplicate words")

        # Exact repeating pattern — catches "ankitankit", "anacondaanaconda"
        if re.search(r'(.{2,})\1+', clean):
            raise ValueError("Theme looks like gibberish — please enter a valid theme")

        # 4+ consecutive same chars — catches "aaaaaaa"
        if re.search(r'(.)\1{3,}', v):
            raise ValueError("Theme looks like gibberish — please enter a valid theme")

        # No vowels — catches "dhfghskgfjh"
        if not re.search(r'[aeiouAEIOU]', v):
            raise ValueError("Theme must contain at least one vowel")

        # Low uniqueness ratio for 8+ char strings — catches "vikashvikas"
        # Only for longer strings — short typos like "aapplee" are allowed
        if len(clean) >= 8:
            ratio = len(set(clean)) / len(clean)
            if ratio < 0.6:
                raise ValueError("Theme looks like gibberish — please enter a valid theme")

        return v


class StoryResponse(BaseModel):
    """
    Response schema for a complete story.
    session_id excluded — internal field, not exposed to client.
    root_node excluded from nodes — no duplicate data in response.
    """
    id: int
    title: str
    created_at: datetime
    root_node: StoryNodeResponse
    nodes: Dict[int, StoryNodeResponse]

    model_config = {"from_attributes": True}