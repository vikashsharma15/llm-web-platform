from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from controllers.job_controller import JobController
from dependencies import get_job_controller, require_active_user
from models.user import User
from utils.constants import StatusCode

router = APIRouter()


@router.get("/{job_id}", status_code=StatusCode.OK)
async def get_job_status(
    job_id:       str,
    current_user: User          = Depends(require_active_user),
    controller:   JobController = Depends(get_job_controller),
) -> JSONResponse:
    """
    Fetch job status by job_id.
    Only the owner can access their job — 403 for others.
    Returns: pending | processing | completed | failed
    """
    return await controller.get_job_status(job_id=job_id, current_user=current_user)