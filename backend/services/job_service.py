import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.job import StoryJob
from repositories.job_repository import JobRepository
from repositories.story_repository import StoryRepository
from core.story_generators import StoryGenerator

logger = logging.getLogger(__name__)


class JobService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def create_job(self, theme: str, session_id: str) -> StoryJob:
        job = StoryJob(
            job_id=str(uuid.uuid4()),
            session_id=session_id,
            theme=theme,
            status="pending",
        )
        try:
            return self.repo.create_job(job)
        except SQLAlchemyError as e:
            logger.error(f"DB error creating job: {e}")
            raise

    def get_job(self, job_id: str) -> StoryJob:
        job = self.repo.get_job_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return job

    # Pointer #11 — LLM sirf background task mein call hoga
    def process_story_job(self, job_id: str, theme: str, session_id: str) -> None:
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            job_repo = JobRepository(db)
            job = job_repo.get_job_by_id(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return

            job.status = "processing"
            job_repo.update_job(job)

            # Pointer #11 — LLM ek baar, sirf yahan
            story = StoryGenerator.generate_story(db, session_id, theme)

            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job_repo.update_job(job)

            logger.info(f"Job {job_id} completed. Story ID: {story.id}")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            try:
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.now(timezone.utc)
                job_repo.update_job(job)
            except Exception:
                pass
        finally:
            db.close()