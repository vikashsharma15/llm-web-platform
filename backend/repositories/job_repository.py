import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.job import StoryJob

logger = logging.getLogger(__name__)


class JobRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_job(self, job: StoryJob) -> StoryJob:
        try:
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)
            return job
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_job_by_id(self, job_id: str) -> StoryJob | None:
        result = await self.db.execute(
            select(StoryJob).where(StoryJob.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_jobs_by_user(self, user_id: int) -> list[StoryJob]:
        """All jobs for a user — for listing endpoint."""
        result = await self.db.execute(
            select(StoryJob)
            .where(StoryJob.user_id == user_id)
            .order_by(StoryJob.created_at.desc())
        )
        return result.scalars().all()

    async def update_job(self, job: StoryJob) -> StoryJob:
        try:
            await self.db.commit()
            await self.db.refresh(job)
            return job
        except SQLAlchemyError:
            await self.db.rollback()
            raise