import uuid
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.job import StoryJob
from repositories.job_repository import JobRepository
from repositories.story_repository import StoryRepository
from core.story_generators import StoryGenerator
from utils.constants import StatusCode, Messages

logger = logging.getLogger(__name__)


def normalize_theme(theme: str) -> str:
    """Normalizes theme for consistent DB lookup — lowercase and stripped."""
    return theme.strip().lower()


class JobService:
    """Handles business logic for story job creation and processing."""

    def __init__(self, db: Session):
        """Injects DB session via dependency injection."""
        self.db = db
        self.repo = JobRepository(db)

    def create_job(self, theme: str, session_id: str) -> StoryJob:
        """Creates a new pending job and saves it to DB."""
        job = StoryJob(
            job_id=str(uuid.uuid4()),
            session_id=session_id,
            theme=normalize_theme(theme),  # normalize before saving
            status="pending",
        )
        return self.repo.create_job(job)

    def get_job(self, job_id: str) -> StoryJob:
        """Fetches job by ID — raises 404 if not found."""
        job = self.repo.get_job_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=StatusCode.NOT_FOUND,
                detail=f"{Messages.JOB_NOT_FOUND}: {job_id}",
            )
        return job

    def process_story_job(self, job_id: str, theme: str, session_id: str) -> None:
        """
        Background task — generates story for a job.
        checks DB cache before calling LLM.
        Uses a separate DB session — background tasks run outside request lifecycle.
        """
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            job_repo = JobRepository(db)
            story_repo = StoryRepository(db)

            job = job_repo.get_job_by_id(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return

            # Mark job as processing before LLM call
            job.status = "processing"
            job_repo.update_job(job)

            normalized = normalize_theme(theme)

            # cache hit: reuse existing story, skip LLM call
            existing_story = story_repo.get_story_by_theme(normalized)
            if existing_story:
                logger.info(f"Cache hit — reusing story for theme: '{normalized}'")
                story = existing_story
            else:
                # Cache miss — call LLM only when necessary
                logger.info(f"Cache miss — calling LLM for theme: '{normalized}'")
                story = StoryGenerator.generate_story(db, session_id, normalized)

            # Mark job as completed with story reference
            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job_repo.update_job(job)

            logger.info(f"Job {job_id} completed — Story ID: {story.id}")

        except Exception as e:
            # Mark job as failed — store error for client polling
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            try:
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.now(timezone.utc)
                job_repo.update_job(job)
            except Exception:
                pass
        finally:
            db.close()  # always close background task session