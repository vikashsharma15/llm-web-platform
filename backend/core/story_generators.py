import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from core.config import get_settings
from models.story import Story, StoryNode
from schemas.llm_schema import StoryLLMResponse, StoryNodeLLM
from prompts.story_prompts import StoryPrompts  # Pointer #10

logger = logging.getLogger(__name__)
settings = get_settings()


class StoryGenerator:
    """Handles LLM story generation and persists result to DB."""

    @classmethod
    def _get_llm(cls) -> ChatGroq:
        """Creates LLM instance using API key from settings."""
        # Pointer #11 — LLM instance created only when needed, not on every request
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.OPENAI_API_KEY,
        )

    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str = "fantasy") -> Story:
        """
        Calls LLM to generate a story, then saves it to DB.
        Pointer #11 — called only from background task, never on every request.
        """
        try:
            llm = cls._get_llm()
            story_parser = PydanticOutputParser(pydantic_object=StoryLLMResponse)

            # Pointer #10 — prompt from StoryPrompts, not hardcoded here
            prompt = ChatPromptTemplate.from_messages([
                ("system", StoryPrompts.STORY_PROMPT),
                ("human", f"Create the story with this theme: {theme}"),
            ]).partial(format_instructions=story_parser.get_format_instructions())

            raw_response = llm.invoke(prompt.invoke({}))
            response_text = raw_response.content if hasattr(raw_response, "content") else raw_response
            story_structure = story_parser.parse(response_text)

            # Pointer #6 — DB error handling
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
            logger.info(f"Story generated for theme: '{theme}', ID: {story_db.id}")
            return story_db

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"DB error while saving story: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"LLM error generating story: {e}")
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
        Builds options list with child node references.
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