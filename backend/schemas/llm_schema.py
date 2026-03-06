from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class StoryOptionLLM(BaseModel):
    """Represents a single choice option returned by LLM."""

    text: str = Field(description="The text of the option shown to the user")
    nextNode: Dict[str, Any] = Field(description="The next node content and its options")


class StoryNodeLLM(BaseModel):
    """Represents a single story node returned by LLM."""

    content: str = Field(description="The main content of the story node")
    isEnding: bool = Field(description="Whether this node is an ending node")
    isWinningEnding: bool = Field(description="Whether this node is a winning ending node")
    options: Optional[List[StoryOptionLLM]] = Field(
        default=None,
        description="The options for this node",
    )


class StoryLLMResponse(BaseModel):
    """
    Top-level schema for parsing LLM story response.
    separate from SQLAlchemy models — only used to parse OpenAI/Groq output.
    """

    title: str = Field(description="The title of the story")
    rootNode: StoryNodeLLM = Field(description="The root node of the story")