"""
Job status polling endpoint.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import JobStatusResponse, ErrorResponse

router = APIRouter()


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Check the status of a processing job",
)
async def get_job_status(job_id: str):
    """
    Poll this endpoint to check the current status of an image processing job.

    Returns the current pipeline step, progress percentage, and any error messages.
    """
    # Import the shared jobs dict from upload module
    from app.api.routes.upload import jobs

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress_percent=job["progress"],
        current_step=job["current_step"],
        message=job["message"],
        created_at=job.get("created_at"),
        completed_at=job.get("completed_at"),
        error=job.get("error"),
    )
