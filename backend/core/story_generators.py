import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser

from core.config import get_settings
from models.story import Story, StoryNode
from schemas.llm_schema import StoryLLMResponse, StoryNodeLLM
from prompts.story_prompts import StoryPrompts

logger   = logging.getLogger(__name__)
settings = get_settings()

MAX_RETRIES = 3


class StoryGenerator:

    @classmethod
    def _get_llm(cls) -> ChatGroq:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.OPENAI_API_KEY,
        )

    @classmethod
    def _build_messages(cls, theme: str) -> list:
        return [
            {"role": "system", "content": StoryPrompts.get_formatted_prompt()},
            {"role": "user",   "content": f"Create the story with this theme: {theme}"},
        ]

    @classmethod
    async def generate_story(cls, db: AsyncSession, user_id: int, theme: str = "fantasy") -> Story:
        """
        Calls LLM → validates → saves to DB.
        Edge cases:
            1. Empty/null LLM response     → retry
            2. Invalid JSON                → retry
            3. All retries exhausted       → ValueError (job marked failed)
            4. SQLAlchemy error on save    → rollback + re-raise
            5. Unexpected error on save    → rollback + re-raise
        """
        llm             = cls._get_llm()
        parser          = PydanticOutputParser(pydantic_object=StoryLLMResponse)
        messages        = cls._build_messages(theme)
        story_structure = None
        last_error      = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"op=llm_call attempt={attempt}/{MAX_RETRIES} theme={theme}")

                raw  = llm.invoke(messages)
                text = raw.content if hasattr(raw, "content") else str(raw)

                if not text or text.strip() in ("null", "", "None"):
                    logger.warning(f"op=llm_call empty_response attempt={attempt}")
                    continue

                try:
                    json.loads(text)
                except json.JSONDecodeError as exc:
                    logger.warning(f"op=llm_call invalid_json attempt={attempt} err={exc}")
                    continue

                story_structure = parser.parse(text)
                logger.info(f"op=llm_call success attempt={attempt} theme={theme}")
                break

            except Exception as exc:
                last_error = exc
                logger.warning(f"op=llm_call exception attempt={attempt} err={exc!r}")
                continue

        if not story_structure:
            raise ValueError(f"LLM failed after {MAX_RETRIES} attempts theme={theme} last_error={last_error}")

        try:
            story_db = Story(
                title=story_structure.title,
                user_id=user_id,               # ← session_id replaced with user_id
                theme=theme,
            )
            db.add(story_db)
            await db.flush()                   # get ID without committing

            root_node_data = story_structure.rootNode
            if isinstance(root_node_data, dict):
                root_node_data = StoryNodeLLM.model_validate(root_node_data)

            await cls._process_story_node(db, story_db.id, root_node_data, is_root=True)

            await db.commit()
            logger.info(f"op=story_saved story_id={story_db.id} theme={theme} uid={user_id}")
            return story_db

        except SQLAlchemyError as exc:
            await db.rollback()
            logger.error(f"op=story_save db_error theme={theme} err={exc!r}")
            raise
        except Exception as exc:
            await db.rollback()
            logger.error(f"op=story_save unexpected_error theme={theme} err={exc!r}")
            raise

    @classmethod
    async def _process_story_node(
        cls,
        db: AsyncSession,
        story_id: int,
        node_data: StoryNodeLLM,
        is_root: bool = False,
    ) -> StoryNode:

        def _get(obj, key):
            return getattr(obj, key) if hasattr(obj, key) else obj[key]

        node = StoryNode(
            story_id=story_id,
            content=_get(node_data, "content"),
            is_root=is_root,
            is_ending=_get(node_data, "isEnding"),
            is_winning_ending=_get(node_data, "isWinningEnding"),
            options=[],
        )
        db.add(node)
        await db.flush()

        if not node.is_ending and hasattr(node_data, "options") and node_data.options:
            options_list = []
            for option_data in node_data.options:
                next_node = option_data.nextNode
                if isinstance(next_node, dict):
                    next_node = StoryNodeLLM.model_validate(next_node)

                child = await cls._process_story_node(db, story_id, next_node, is_root=False)
                options_list.append({
                    "text":    option_data.text,
                    "node_id": child.id,
                })

            node.options = options_list
            await db.flush()

        return node