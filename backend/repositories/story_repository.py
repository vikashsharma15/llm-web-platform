import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models.story import Story, StoryNode

logger = logging.getLogger(__name__)


class StoryRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_story_by_id(self, story_id: int) -> Story | None:
        result = await self.db.execute(
            select(Story)
            .where(Story.id == story_id)
            .options(selectinload(Story.nodes))   # ← eager load nodes, avoid N+1
        )
        return result.scalar_one_or_none()

    async def get_story_by_theme(self, theme: str) -> Story | None:
        """Cache check — reuse existing story, skip LLM."""
        result = await self.db.execute(
            select(Story).where(Story.theme == theme)
        )
        return result.scalar_one_or_none()

    async def get_stories_by_user(self, user_id: int) -> list[Story]:
        result = await self.db.execute(
            select(Story)
            .where(Story.user_id == user_id)
            .order_by(Story.created_at.desc())
        )
        return result.scalars().all()

    async def create_story(self, story: Story) -> Story:
        try:
            self.db.add(story)
            await self.db.commit()
            await self.db.refresh(story)
            return story
        except SQLAlchemyError:
            await self.db.rollback()
            raise