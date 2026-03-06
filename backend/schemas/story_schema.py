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
        Validates theme — rejects clear gibberish before wasting an LLM call.
        Intentionally lenient — allows typos and real words like Globetrotter.
        LLM handles typo correction via prompt instructions.
        """
        # Empty check before strip — catches ""
        if not v:
            raise ValueError("Theme cannot be empty")

        # Whitespace only check — catches "   "
        if not v.strip():
            raise ValueError("Theme cannot be whitespace only")

        v = v.strip()

        if len(v) < 3:
            raise ValueError("Theme must be at least 3 characters long")

        if len(v) > 30:
            raise ValueError("Theme must be at most 30 characters long")

        # Only letters, numbers and spaces — no special chars
        if not re.match(r'^[a-zA-Z0-9\s]+$', v):
            raise ValueError("Theme must contain only letters, numbers and spaces")

        words = v.split()

        # Max 3 words — "dark fantasy forest" ok, "a b c d e" not
        if len(words) > 3:
            raise ValueError("Theme must be at most 3 words")

        # No duplicate words — catches "space space"
        if len(words) != len(set(w.lower() for w in words)):
            raise ValueError("Theme must not contain duplicate words")

        # Repeating pattern 4+ chars — catches "ankitankit", "anacondaanaconda"
        # 4+ threshold allows real words like "Mississippi", "Globetrotter"
        clean = v.replace(" ", "").lower()
        if re.search(r'(.{4,})\1+', clean):
            raise ValueError("Theme looks like gibberish — please enter a valid theme")

        # 4+ consecutive same chars — catches "aaaaaaa", "lllzzz"
        if re.search(r'(.)\1{4,}', v):
            raise ValueError("Theme looks like gibberish — please enter a valid theme")

        # No vowels at all — catches "dhfghskgfjh", "zxcvbn"
        if not re.search(r'[aeiouAEIOU]', v):
            raise ValueError("Theme must contain at least one vowel")

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