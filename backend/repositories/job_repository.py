from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.job import StoryJob


class JobRepository:
    """Handles all DB operations for StoryJob model."""

    def __init__(self, db: Session):
        self.db = db

    def create_job(self, job: StoryJob) -> StoryJob:
        """Inserts a new job record into DB."""
        try:
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def get_job_by_id(self, job_id: str) -> StoryJob | None:
        """Fetches job by UUID job_id — returns None if not found."""
        return self.db.query(StoryJob).filter(StoryJob.job_id == job_id).first()

    def update_job(self, job: StoryJob) -> StoryJob:
        """Commits any changes made to an existing job object."""
        try:
            self.db.commit()
            self.db.refresh(job)
            return job
        except SQLAlchemyError:
            self.db.rollback()
            raise