import logging

from sqlalchemy.orm import Session

from repositories.story_repository import StoryRepository
from schemas.story import StoryNodeResponse, StoryResponse, StoryOptionSchema

logger = logging.getLogger(__name__)


class StoryService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = StoryRepository(db)

    def get_complete_story(self, story_id: int) -> StoryResponse:
        story = self.repo.get_story_by_id(story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        nodes = self.repo.get_nodes_by_story_id(story_id)
        if not nodes:
            raise ValueError(f"No nodes found for story {story_id}")

        node_map: dict[int, StoryNodeResponse] = {
            node.id: StoryNodeResponse(
                id=node.id,
                content=node.content,
                is_ending=node.is_ending,
                is_winning_ending=node.is_winning_ending,
                options=[StoryOptionSchema(**opt) for opt in (node.options or [])],
            )
            for node in nodes
        }

        root_node = next((n for n in nodes if n.is_root), None)
        if not root_node:
            raise ValueError(f"Root node not found for story {story_id}")

        return StoryResponse(
            id=story.id,
            title=story.title,
            session_id=story.session_id,
            created_at=story.created_at,
            root_node=node_map[root_node.id],
            all_nodes=node_map,
        )