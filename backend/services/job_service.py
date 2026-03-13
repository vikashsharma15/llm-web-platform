import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.job import StoryJob
from repositories.job_repository import JobRepository
from repositories.story_repository import StoryRepository
from core.story_generators import StoryGenerator
from utils.constants import StatusCode, Messages, ErrorCode
from utils.exceptions import raise_http_error
from schemas.job_schema import StoryJobResponse 
logger = logging.getLogger(__name__)


def normalize_theme(theme: str) -> str:
    return theme.strip().lower()


class JobService:

    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.repo = JobRepository(db)

    async def create_job(self, theme: str, user_id: int) -> dict:  # ← dict
        job = StoryJob(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            theme=normalize_theme(theme),
            status="pending",
        )
        created = await self.repo.create_job(job)
        return StoryJobResponse.model_validate(created).model_dump(mode="json") 

    async def get_job(self, job_id: str, user_id: int) -> dict: 
        if not job_id or not job_id.strip():
            raise_http_error(StatusCode.BAD_REQUEST, ErrorCode.BAD_REQUEST, Messages.INVALID_JOB_ID)

        job = await self.repo.get_job_by_id(job_id)
        if not job:
            raise_http_error(StatusCode.NOT_FOUND, ErrorCode.NOT_FOUND, Messages.JOB_NOT_FOUND)

        if job.user_id != user_id:
            raise_http_error(StatusCode.FORBIDDEN, ErrorCode.FORBIDDEN, Messages.FORBIDDEN)

        return StoryJobResponse.model_validate(job).model_dump(mode="json")

    async def process_story_job(self, job_id: str, theme: str, user_id: int) -> None:
        """
        Background task — own session, never raises.
        Marks job failed on any exception — client polls for status.
        """
        from db.database import AsyncSessionLocal
        job = None

        async with AsyncSessionLocal() as db:
            job_repo   = JobRepository(db)
            story_repo = StoryRepository(db)

            job = await job_repo.get_job_by_id(job_id)
            if not job:
                logger.error(f"op=process_story_job job_not_found job_id={job_id}")
                return

            # Guard — prevent double processing if task queued twice
            if job.status not in ("pending",):
                logger.warning(f"op=process_story_job skip status={job.status} job_id={job_id}")
                return

            try:
                job.status = "processing"
                await job_repo.update_job(job)

                normalized     = normalize_theme(theme)
                existing_story = await story_repo.get_story_by_theme(normalized)

                if existing_story:
                    logger.info(f"op=process_story_job cache_hit theme={normalized}")
                    story = existing_story
                else:
                    logger.info(f"op=process_story_job cache_miss theme={normalized}")
                    story = await StoryGenerator.generate_story(db, user_id, normalized)

                job.story_id     = story.id
                job.status       = "completed"
                job.completed_at = datetime.now(timezone.utc)
                await job_repo.update_job(job)

                logger.info(f"op=process_story_job completed job_id={job_id} story_id={story.id}")

            except Exception as exc:
                logger.error(f"op=process_story_job failed job_id={job_id} err={exc!r}", exc_info=True)
                try:
                    if job:
                        job.status       = "failed"
                        job.error        = str(exc)[:500]
                        job.completed_at = datetime.now(timezone.utc)
                        await job_repo.update_job(job)
                except Exception:
                    pass