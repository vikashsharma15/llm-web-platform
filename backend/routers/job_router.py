from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from controllers.job_controller import JobController
from routers.dependencies import get_job_controller

# Module level — created once on app startup, not on every request
router = APIRouter()


@router.get("/{job_id}", status_code=200)
def get_job_status(
    job_id: str,
    controller: JobController = Depends(get_job_controller),
) -> JSONResponse:
    """Fetches current status of a story generation job by job_id."""
    return controller.get_job_status(job_id=job_id)