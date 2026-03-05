import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models.story import Story, StoryNode
from core.llm_schemas import StoryLLMResponse, StoryNodeLLM

# Pointer #10 — prompt ab prompts/ folder se aata hai, core se nahi
from prompts.story_prompts import StoryPrompts

load_dotenv()


class StoryGenerator:

    @classmethod
    def _get_llm(cls) -> ChatGroq:
        # Pointer #11 — LLM instance sirf generate_story call pe banta hai
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str = "fantasy") -> Story:
        llm = cls._get_llm()
        story_parser = PydanticOutputParser(pydantic_object=StoryLLMResponse)

        # Pointer #10 — STORY_PROMPT ab StoryPrompts class se aata hai
        prompt = ChatPromptTemplate.from_messages([
            ("system", StoryPrompts.STORY_PROMPT),
            ("human", f"Create the story with this theme: {theme}"),
        ]).partial(format_instructions=story_parser.get_format_instructions())

        raw_response = llm.invoke(prompt.invoke({}))

        response_text = raw_response.content if hasattr(raw_response, "content") else raw_response
        story_structure = story_parser.parse(response_text)

        # Save story to DB
        story_db = Story(title=story_structure.title, session_id=session_id)
        db.add(story_db)
        db.flush()

        root_node_data = story_structure.rootNode
        if isinstance(root_node_data, dict):
            root_node_data = StoryNodeLLM.model_validate(root_node_data)

        cls._process_story_node(db, story_db.id, root_node_data, is_root=True)

        db.commit()
        return story_db

    @classmethod
    def _process_story_node(
        cls,
        db: Session,
        story_id: int,
        node_data: StoryNodeLLM,
        is_root: bool = False,
    ) -> StoryNode:

        # Helper to safely get attribute or dict key
        def get(obj, key):
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