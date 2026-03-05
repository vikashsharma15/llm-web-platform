from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# Pointer #10 — LLM response ke liye alag schemas
# SQLAlchemy models se alag — yeh sirf OpenAI response parse karta hai

class StoryOptionLLM(BaseModel):
    text: str = Field(description="The text of the option shown to the user")
    nextNode: Dict[str, Any] = Field(description="The next node content and its options")


class StoryNodeLLM(BaseModel):
    content: str = Field(description="The main content of the story node")
    isEnding: bool = Field(description="Whether this node is an ending node")
    isWinningEnding: bool = Field(description="Whether this node is a winning ending node")
    options: Optional[List[StoryOptionLLM]] = Field(default=None, description="The options for this node")


class StoryLLMResponse(BaseModel):
    title: str = Field(description="The title of the story")
    rootNode: StoryNodeLLM = Field(description="The root node of the story")