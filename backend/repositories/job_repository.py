from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.job import StoryJob


class JobRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_job(self, job: StoryJob) -> StoryJob:
        try:
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_job_by_id(self, job_id: str) -> StoryJob | None:
        return self.db.query(StoryJob).filter(StoryJob.job_id == job_id).first()

    def update_job(self, job: StoryJob) -> StoryJob:
        try:
            self.db.commit()
            self.db.refresh(job)
            return job
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e