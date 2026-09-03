"""
Image upload API endpoint.
Accepts two Chandrayaan-2 image files and starts the processing pipeline.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from loguru import logger

from app.core.config import settings
from app.models.schemas import UploadResponse, ErrorResponse, JobStatus
from app.services.pipeline import ProcessingPipeline

router = APIRouter()

# In-memory job store (replace with Redis/DB in production)
jobs: dict = {}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".img", ".tif", ".tiff", ".geotiff", ".lbl", ".fits", ".png", ".jpg", ".jpeg"}


def _validate_file(file: UploadFile) -> None:
    """Validate uploaded file type and size."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )


async def _save_upload(file: UploadFile, job_dir: Path) -> Path:
    """Save an uploaded file to the job directory."""
    filepath = job_dir / file.filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info(f"Saved upload: {filepath} ({filepath.stat().st_size / 1024:.1f} KB)")
    return filepath


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Upload two Chandrayaan-2 images for correspondence matching",
)
async def upload_images(
    background_tasks: BackgroundTasks,
    image_a: UploadFile = File(..., description="First Chandrayaan-2 image (OHRC/TMC/IIRS)"),
    image_b: UploadFile = File(..., description="Second Chandrayaan-2 image (different instrument/scale)"),
):
    """
    Upload two Chandrayaan-2 images to find feature correspondences.

    The system will:
    1. Parse the files and extract spatial metadata
    2. Preprocess each image based on its instrument type
    3. Run LoFTR-based deep feature matching
    4. Verify matches with MAGSAC++
    5. Map pixel coordinates to Lunar lat/lon
    6. Return matched features with confidence scores
    """
    # Validate both files
    _validate_file(image_a)
    _validate_file(image_b)

    # Create job
    job_id = str(uuid.uuid4())
    job_dir = settings.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded files
    try:
        path_a = await _save_upload(image_a, job_dir)
        path_b = await _save_upload(image_b, job_dir)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save files: {str(e)}")

    # Initialize job record
    response = UploadResponse(job_id=job_id)
    jobs[job_id] = {
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "current_step": "Queued",
        "message": "Processing will begin shortly.",
        "image_a_path": str(path_a),
        "image_b_path": str(path_b),
        "created_at": response.created_at,
        "completed_at": None,
        "result": None,
        "error": None,
    }

    # Start processing in background
    background_tasks.add_task(_run_pipeline, job_id, str(path_a), str(path_b))

    logger.info(f"Job {job_id} created: {image_a.filename} ↔ {image_b.filename}")
    return response


async def _run_pipeline(job_id: str, path_a: str, path_b: str):
    """Run the full processing pipeline as a background task."""
    from datetime import datetime

    pipeline = ProcessingPipeline()

    def progress_callback(status: JobStatus, progress: float, step: str, message: str):
        """Update job status as pipeline progresses."""
        jobs[job_id]["status"] = status
        jobs[job_id]["progress"] = progress
        jobs[job_id]["current_step"] = step
        jobs[job_id]["message"] = message

    try:
        result = await pipeline.run(path_a, path_b, progress_callback)
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["progress"] = 100.0
        jobs[job_id]["current_step"] = "Completed"
        jobs[job_id]["message"] = "Processing complete."
        jobs[job_id]["completed_at"] = datetime.utcnow()
        jobs[job_id]["result"] = result
        logger.success(f"Job {job_id} completed successfully.")
    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Processing failed: {str(e)}"
        logger.error(f"Job {job_id} failed: {e}")
