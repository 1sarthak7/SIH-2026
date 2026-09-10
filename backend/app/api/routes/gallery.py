"""
Gallery & Live Demo routes.

Lists available Chandrayaan-2 images from the Data directory
and runs the pipeline on selected image pairs — no file upload needed.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.ingestion import _parse_pds4_xml, _find_product_files
from app.services.pipeline import ProcessingPipeline
from app.models.schemas import JobStatus

router = APIRouter(prefix="/api/gallery", tags=["Gallery"])

# Where the data lives (mounted Google Drive in Colab)
DATA_DIR = os.environ.get("DATA_DIR", "/content/SIH-2026/Data")

# In-memory job store for demo runs
_demo_jobs: dict = {}


class GalleryImage(BaseModel):
    id: str
    instrument: str
    filename: str
    directory: str
    width: int
    height: int
    resolution_m: float
    sun_elevation: Optional[float] = None
    sun_azimuth: Optional[float] = None
    area: Optional[str] = None
    acquisition_date: Optional[str] = None
    thumbnail_url: Optional[str] = None
    lat_range: Optional[str] = None
    lon_range: Optional[str] = None


class DemoRunRequest(BaseModel):
    image_a_id: str
    image_b_id: str


class DemoRunResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.get("/images", response_model=list[GalleryImage])
async def list_gallery_images():
    """List all available Chandrayaan-2 images from the data directory."""
    images = []

    if not os.path.exists(DATA_DIR):
        logger.warning(f"Data directory not found: {DATA_DIR}")
        return images

    for instrument_dir in sorted(Path(DATA_DIR).iterdir()):
        if not instrument_dir.is_dir() or instrument_dir.name.startswith("."):
            continue

        instrument_name = instrument_dir.name  # "OHRC", "TMC", "IIRS"

        for product_dir in sorted(instrument_dir.iterdir()):
            if not product_dir.is_dir() or product_dir.name.startswith("."):
                continue

            try:
                files = _find_product_files(str(product_dir))
                if not files.get("label"):
                    continue

                meta = _parse_pds4_xml(files["label"])

                # Get lat/lon range
                lats = [meta.get(k, 0) for k in ["ul_lat", "ur_lat", "ll_lat", "lr_lat"]]
                lons = [meta.get(k, 0) for k in ["ul_lon", "ur_lon", "ll_lon", "lr_lon"]]
                lat_range = f"{min(lats):.2f}° to {max(lats):.2f}°" if any(lats) else None
                lon_range = f"{min(lons):.2f}° to {max(lons):.2f}°" if any(lons) else None

                # Build thumbnail URL if browse PNG exists
                thumb_url = None
                if files.get("browse_png"):
                    thumb_url = f"/api/gallery/thumbnail/{instrument_name}/{product_dir.name}"

                images.append(GalleryImage(
                    id=f"{instrument_name}/{product_dir.name}",
                    instrument=instrument_name,
                    filename=product_dir.name,
                    directory=str(product_dir),
                    width=meta.get("samples", 0),
                    height=meta.get("lines", 0),
                    resolution_m=meta.get("resolution_m", 0),
                    sun_elevation=meta.get("sun_elevation"),
                    sun_azimuth=meta.get("sun_azimuth"),
                    area=meta.get("area"),
                    acquisition_date=meta.get("acquisition_date"),
                    thumbnail_url=thumb_url,
                    lat_range=lat_range,
                    lon_range=lon_range,
                ))

            except Exception as e:
                logger.warning(f"Could not parse {product_dir.name}: {e}")
                continue

    logger.info(f"Gallery: found {len(images)} images in {DATA_DIR}")
    return images


@router.get("/thumbnail/{instrument}/{product_name}")
async def get_thumbnail(instrument: str, product_name: str):
    """Serve the browse PNG thumbnail for a product."""
    from fastapi.responses import FileResponse

    product_path = Path(DATA_DIR) / instrument / product_name
    if not product_path.exists():
        raise HTTPException(404, "Product not found")

    # Find browse PNG
    png_files = list(product_path.rglob("*_b_brw_*.png"))
    if not png_files:
        raise HTTPException(404, "No thumbnail available")

    return FileResponse(str(png_files[0]), media_type="image/png")


@router.post("/run", response_model=DemoRunResponse)
async def run_demo(request: DemoRunRequest, background_tasks: BackgroundTasks):
    """Start a demo pipeline run on two pre-loaded images."""
    import uuid

    # Resolve paths
    path_a = str(Path(DATA_DIR) / request.image_a_id)
    path_b = str(Path(DATA_DIR) / request.image_b_id)

    if not os.path.exists(path_a):
        raise HTTPException(404, f"Image A not found: {request.image_a_id}")
    if not os.path.exists(path_b):
        raise HTTPException(404, f"Image B not found: {request.image_b_id}")

    job_id = f"demo-{uuid.uuid4().hex[:8]}"

    _demo_jobs[job_id] = {
        "status": "queued",
        "progress_percent": 0,
        "current_step": "Initializing",
        "message": "Starting pipeline...",
        "result": None,
        "error": None,
    }

    background_tasks.add_task(_run_pipeline_task, job_id, path_a, path_b)

    return DemoRunResponse(
        job_id=job_id,
        status="queued",
        message=f"Pipeline started for {request.image_a_id} ↔ {request.image_b_id}",
    )


async def _run_pipeline_task(job_id: str, path_a: str, path_b: str):
    """Background task that runs the full pipeline in a thread executor."""
    import asyncio
    import traceback

    try:
        def progress_callback(status, progress, step, message):
            _demo_jobs[job_id].update({
                "status": status.value if hasattr(status, 'value') else str(status),
                "progress_percent": progress,
                "current_step": step,
                "message": message,
            })

        _demo_jobs[job_id]["status"] = "processing"
        _demo_jobs[job_id]["message"] = "Initializing pipeline..."

        # Run the blocking pipeline in a thread so event loop stays responsive
        loop = asyncio.get_event_loop()

        def _run_sync():
            """Synchronous wrapper that runs the async pipeline."""
            import asyncio as _asyncio
            _loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(_loop)
            try:
                pipeline = ProcessingPipeline()
                return _loop.run_until_complete(
                    pipeline.run(path_a, path_b, progress_callback=progress_callback)
                )
            finally:
                _loop.close()

        result = await loop.run_in_executor(None, _run_sync)

        # Serialize to dict for JSON response
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        result_dict["job_id"] = job_id

        _demo_jobs[job_id]["status"] = "completed"
        _demo_jobs[job_id]["progress_percent"] = 100
        _demo_jobs[job_id]["result"] = result_dict

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Demo pipeline failed: {e}\n{tb}")
        _demo_jobs[job_id]["status"] = "failed"
        _demo_jobs[job_id]["error"] = str(e)


@router.get("/status/{job_id}")
async def get_demo_status(job_id: str):
    """Get the status of a demo pipeline run."""
    if job_id not in _demo_jobs:
        raise HTTPException(404, "Job not found")

    job = _demo_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress_percent": job["progress_percent"],
        "current_step": job["current_step"],
        "message": job["message"],
        "error": job.get("error"),
    }


@router.get("/results/{job_id}")
async def get_demo_results(job_id: str):
    """Get the results of a completed demo pipeline run."""
    if job_id not in _demo_jobs:
        raise HTTPException(404, "Job not found")

    job = _demo_jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Job not completed yet: {job['status']}")

    if not job.get("result"):
        raise HTTPException(500, "No results available")

    return job["result"]
