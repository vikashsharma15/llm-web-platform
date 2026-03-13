import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.story_repository import StoryRepository
from schemas.story_schema import StoryNodeResponse, StoryOptionSchema, StoryResponse
from utils.constants import ErrorCode, Messages, StatusCode
from utils.exceptions import raise_http_error

logger = logging.getLogger(__name__)


class StoryService:

    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.repo = StoryRepository(db)

    async def get_complete_story(self, story_id: int, user_id: int) -> dict:
        rid = uuid.uuid4().hex[:12]                

        logger.info(f"rid={rid} op=get_complete_story story_id={story_id} uid={user_id}")

        if story_id <= 0:
            raise_http_error(StatusCode.BAD_REQUEST, ErrorCode.BAD_REQUEST, Messages.INVALID_STORY_ID)

        story = await self.repo.get_story_by_id(story_id)
        if not story:
            logger.warning(f"rid={rid} op=get_complete_story story_not_found story_id={story_id}")
            raise_http_error(StatusCode.NOT_FOUND, ErrorCode.NOT_FOUND, Messages.STORY_NOT_FOUND)

        if story.user_id != user_id:
            logger.warning(f"rid={rid} op=get_complete_story forbidden story_id={story_id} uid={user_id}")
            raise_http_error(StatusCode.FORBIDDEN, ErrorCode.FORBIDDEN, Messages.FORBIDDEN)

        nodes = story.nodes
        if not nodes:
            logger.warning(f"rid={rid} op=get_complete_story no_nodes story_id={story_id}")
            raise_http_error(StatusCode.NOT_FOUND, ErrorCode.NOT_FOUND, Messages.STORY_NODES_NOT_FOUND)

        root_node = next((n for n in nodes if n.is_root), None)
        if not root_node:
            logger.error(f"rid={rid} op=get_complete_story no_root story_id={story_id} uid={user_id}")
            raise_http_error(StatusCode.INTERNAL_SERVER_ERROR, ErrorCode.SERVER_ERROR, Messages.STORY_ROOT_NOT_FOUND)

        def build_node(node) -> StoryNodeResponse:
            return StoryNodeResponse(
                id=node.id,
                content=node.content,
                is_ending=node.is_ending,
                is_winning_ending=node.is_winning_ending,
                options=[StoryOptionSchema(**opt) for opt in (node.options or [])],
            )

        node_map = {
            node.id: build_node(node)
            for node in nodes
            if not node.is_root
        }

        logger.info(f"rid={rid} op=get_complete_story success story_id={story_id} uid={user_id}")

        return StoryResponse(
            id=story.id,
            title=story.title,
            created_at=story.created_at,
            root_node=build_node(root_node),
            nodes=node_map,
        ).model_dump(mode="json")                   