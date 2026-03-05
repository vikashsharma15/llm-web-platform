from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class StoryOptionSchema(BaseModel):
    text: str
    node_id: Optional[int] = None


class StoryNodeResponse(BaseModel):
    id: int
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False
    options: List[StoryOptionSchema] = []

    model_config = {"from_attributes": True}


class CreateStoryRequest(BaseModel):
    theme: str

    @field_validator("theme")
    @classmethod
    def theme_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Theme cannot be empty or whitespace")
        return v.strip()


class StoryResponse(BaseModel):
    id: int
    title: str
    session_id: Optional[str] = None
    created_at: datetime
    root_node: StoryNodeResponse
    all_nodes: Dict[int, StoryNodeResponse]

    model_config = {"from_attributes": True}