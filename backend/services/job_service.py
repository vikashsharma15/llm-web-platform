import uuid
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.job import StoryJob
from repositories.job_repository import JobRepository
from repositories.story_repository import StoryRepository
from core.story_generators import StoryGenerator

logger = logging.getLogger(__name__)


class JobService:
    """Handles business logic for story job creation and processing."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def create_job(self, theme: str, session_id: str) -> StoryJob:
        """Creates a new pending job and saves it to DB."""
        job = StoryJob(
            job_id=str(uuid.uuid4()),
            session_id=session_id,
            theme=theme,
            status="pending",
        )
        return self.repo.create_job(job)

    def get_job(self, job_id: str) -> StoryJob:
        """Fetches job by ID — raises 404 if not found."""
        job = self.repo.get_job_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        return job

    def process_story_job(self, job_id: str, theme: str, session_id: str) -> None:
        """
        Background task — processes story generation for a job.
        Pointer #11 — checks DB cache before calling LLM.
        If story for same theme exists, reuses it — avoids redundant LLM calls.
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

            # Mark job as processing before starting LLM call
            job.status = "processing"
            job_repo.update_job(job)

            # Pointer #11 — reuse existing story if same theme found in DB
            existing_story = story_repo.get_story_by_theme(theme)
            if existing_story:
                logger.info(f"Cache hit — reusing story for theme: '{theme}'")
                story = existing_story
            else:
                # Cache miss — call LLM only when necessary
                logger.info(f"Cache miss — calling LLM for theme: '{theme}'")
                story = StoryGenerator.generate_story(db, session_id, theme)

            # Mark job as completed with story reference
            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job_repo.update_job(job)

            logger.info(f"Job {job_id} completed. Story ID: {story.id}")

        except Exception as e:
            # Mark job as failed and store error message
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