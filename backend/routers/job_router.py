from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db.database import get_db
from controllers.job_controller import JobController
from services.job_service import JobService


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", status_code=200)
def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JSONResponse:
    controller = JobController(job_service)
    return controller.get_job_status(job_id=job_id)