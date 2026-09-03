"""
Results retrieval endpoint.
Returns the full matching results for a completed job.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.config import settings
from app.models.schemas import ResultsResponse, ErrorResponse, JobStatus

router = APIRouter()


@router.get(
    "/results/{job_id}",
    response_model=ResultsResponse,
    responses={
        404: {"model": ErrorResponse},
        202: {"model": ErrorResponse},
    },
    summary="Get the full matching results for a completed job",
)
async def get_results(job_id: str):
    """
    Retrieve the complete results for a processed image pair.

    Returns matched feature coordinates (pixel + lunar), confidence scores,
    and processing statistics. Only available after job status is 'completed'.
    """
    from app.api.routes.upload import jobs

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]

    if job["status"] == JobStatus.FAILED:
        raise HTTPException(
            status_code=500,
            detail=f"Job failed: {job.get('error', 'Unknown error')}"
        )

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=202,
            detail=f"Job is still processing. Current status: {job['status'].value}"
        )

    if not job.get("result"):
        raise HTTPException(
            status_code=500,
            detail="Job completed but no results were generated."
        )

    return job["result"]


@router.get(
    "/results/{job_id}/image/{which}",
    summary="Get the processed image (for frontend display)",
)
async def get_processed_image(job_id: str, which: str):
    """
    Serve a processed image for frontend visualization.
    `which` should be 'a' or 'b'.
    """
    from app.api.routes.upload import jobs

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]
    key = f"image_{which}_path"

    if key not in job:
        raise HTTPException(status_code=400, detail=f"Invalid image identifier: '{which}'")

    filepath = Path(job[key])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk.")

    # For display, we serve the preprocessed PNG version if available
    png_path = filepath.with_suffix(".preview.png")
    if png_path.exists():
        return FileResponse(png_path, media_type="image/png")

    # Fallback to original (browser may not render .img/.tif directly)
    return FileResponse(str(filepath))
