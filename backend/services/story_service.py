import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from repositories.story_repository import StoryRepository
from schemas.story_schema import StoryNodeResponse, StoryResponse, StoryOptionSchema
from utils.constants import StatusCode, Messages

logger = logging.getLogger(__name__)


class StoryService:
    """Handles business logic for fetching and assembling complete stories."""

    def __init__(self, db: Session):
        """Injects DB session via dependency injection."""
        self.db = db
        self.repo = StoryRepository(db)

    def get_complete_story(self, story_id: int) -> StoryResponse:
        """
        Fetches story with all nodes and assembles into StoryResponse.
        session_id excluded from response — internal field only.
        root_node excluded from nodes dict — no duplicate data sent to client.
        """
        story = self.repo.get_story_by_id(story_id)
        if not story:
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND,
                detail=f"{Messages.STORY_NOT_FOUND}: {story_id}",
            )

        nodes = self.repo.get_nodes_by_story_id(story_id)
        if not nodes:
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND,
                detail=Messages.STORY_NODES_NOT_FOUND,
            )

        # Find root node — entry point of the story
        root_node = next((n for n in nodes if n.is_root), None)
        if not root_node:
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND,
                detail=Messages.STORY_ROOT_NOT_FOUND,
            )

        # Build node map — root excluded to avoid duplicate data in response
        node_map: dict[int, StoryNodeResponse] = {
            node.id: StoryNodeResponse(
                id=node.id,
                content=node.content,
                is_ending=node.is_ending,
                is_winning_ending=node.is_winning_ending,
                options=[StoryOptionSchema(**opt) for opt in (node.options or [])],
            )
            for node in nodes
            if not node.is_root
        }

        return StoryResponse(
            id=story.id,
            title=story.title,
            created_at=story.created_at,
            root_node=StoryNodeResponse(
                id=root_node.id,
                content=root_node.content,
                is_ending=root_node.is_ending,
                is_winning_ending=root_node.is_winning_ending,
                options=[StoryOptionSchema(**opt) for opt in (root_node.options or [])],
            ),
            nodes=node_map,
        )