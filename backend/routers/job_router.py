from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from controllers.job_controller import JobController
from dependencies import get_job_controller
from utils.constants import StatusCode

# No prefix/tags here — defined in router_registry.py
router = APIRouter()


@router.get("/{job_id}", status_code=StatusCode.OK)
def get_job_status(
    job_id: str,
    controller: JobController = Depends(get_job_controller),
) -> JSONResponse:
    """Fetches current status of a story generation job by job_id."""
    return controller.get_job_status(job_id=job_id)