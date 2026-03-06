import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser

from core.config import get_settings
from models.story import Story, StoryNode
from schemas.llm_schema import StoryLLMResponse, StoryNodeLLM
from prompts.story_prompts import StoryPrompts  # Pointer #10

logger = logging.getLogger(__name__)
settings = get_settings()

# 3 retries — balances reliability vs API cost
MAX_RETRIES = 3


class StoryGenerator:
    """Handles LLM story generation and persists result to DB."""

    @classmethod
    def _get_llm(cls) -> ChatGroq:
        """Creates LLM instance — uses API key from settings."""
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.OPENAI_API_KEY,
        )

    @classmethod
    def _build_messages(cls, theme: str) -> list:
        """
        Builds message list for LLM invocation.
        Pointer #10 — uses pre-formatted prompt from StoryPrompts.
        JSON structure already injected via get_formatted_prompt().
        """
        return [
            {"role": "system", "content": StoryPrompts.get_formatted_prompt()},
            {"role": "user",   "content": f"Create the story with this theme: {theme}"},
        ]

    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str = "fantasy") -> Story:
        """
        Calls LLM to generate a branching story, then persists to DB.
        Pointer #11 — only called on cache miss, never on every request.
        Retries up to MAX_RETRIES on null or invalid JSON response.
        """
        llm = cls._get_llm()
        story_parser = PydanticOutputParser(pydantic_object=StoryLLMResponse)
        messages = cls._build_messages(theme)

        story_structure = None
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"LLM attempt {attempt}/{MAX_RETRIES} for theme: '{theme}'")

                raw_response = llm.invoke(messages)
                response_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)

                # Guard — null or empty response
                if not response_text or response_text.strip() in ("null", "", "None"):
                    logger.warning(f"LLM returned empty response on attempt {attempt} — retrying")
                    continue

                # Guard — invalid JSON before Pydantic parse
                try:
                    json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on attempt {attempt}: {e} — retrying")
                    continue

                story_structure = story_parser.parse(response_text)
                logger.info(f"LLM parse success on attempt {attempt}")
                break

            except Exception as e:
                last_error = e
                logger.warning(f"LLM attempt {attempt} failed: {e}")
                continue

        if not story_structure:
            raise ValueError(f"LLM failed after {MAX_RETRIES} attempts. Last error: {last_error}")

        try:
            story_db = Story(
                title=story_structure.title,
                session_id=session_id,
                theme=theme,  # Pointer #11 — saved for cache lookup
            )
            db.add(story_db)
            db.flush()

            root_node_data = story_structure.rootNode
            if isinstance(root_node_data, dict):
                root_node_data = StoryNodeLLM.model_validate(root_node_data)

            cls._process_story_node(db, story_db.id, root_node_data, is_root=True)

            db.commit()
            logger.info(f"Story saved — theme: '{theme}', ID: {story_db.id}")
            return story_db

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error saving story: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving story: {e}")
            raise

    @classmethod
    def _process_story_node(
        cls,
        db: Session,
        story_id: int,
        node_data: StoryNodeLLM,
        is_root: bool = False,
    ) -> StoryNode:
        """
        Recursively saves story nodes to DB.
        Builds options list with child node IDs.
        """
        def get(obj, key):
            """Gets attribute from object or dict key."""
            return getattr(obj, key) if hasattr(obj, key) else obj[key]

        node = StoryNode(
            story_id=story_id,
            content=get(node_data, "content"),
            is_root=is_root,
            is_ending=get(node_data, "isEnding"),
            is_winning_ending=get(node_data, "isWinningEnding"),
            options=[],
        )
        db.add(node)
        db.flush()

        # Recursively process child nodes and build options list
        if not node.is_ending and hasattr(node_data, "options") and node_data.options:
            options_list = []
            for option_data in node_data.options:
                next_node = option_data.nextNode
                if isinstance(next_node, dict):
                    next_node = StoryNodeLLM.model_validate(next_node)

                child_node = cls._process_story_node(db, story_id, next_node, is_root=False)
                options_list.append({
                    "text": option_data.text,
                    "node_id": child_node.id,
                })

            node.options = options_list
            db.flush()

        return node