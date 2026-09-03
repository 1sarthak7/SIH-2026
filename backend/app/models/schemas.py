"""
Pydantic models for API request/response schemas and internal data structures.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class InstrumentType(str, Enum):
    """Chandrayaan-2 imaging instruments."""
    OHRC = "ohrc"
    TMC = "tmc"
    IIRS = "iirs"
    UNKNOWN = "unknown"


class JobStatus(str, Enum):
    """Pipeline processing status."""
    QUEUED = "queued"
    INGESTING = "ingesting"
    PREPROCESSING = "preprocessing"
    MATCHING = "matching"
    VERIFYING = "verifying"
    MAPPING = "mapping"
    COMPLETED = "completed"
    FAILED = "failed"


# ──────────────────────────────────────────────
# Internal Data Models (not serialized to JSON)
# ──────────────────────────────────────────────

class ImageMetadata(BaseModel):
    """Spatial metadata extracted from a Chandrayaan-2 image file."""
    instrument: InstrumentType
    filepath: str
    width: int
    height: int
    num_bands: int
    resolution_m: float  # meters per pixel
    crs: str  # Coordinate Reference System (e.g., "IAU_2015:30100")
    bbox_lat_min: float
    bbox_lat_max: float
    bbox_lon_min: float
    bbox_lon_max: float
    sun_elevation: Optional[float] = None  # degrees
    sun_azimuth: Optional[float] = None  # degrees
    acquisition_date: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class Patch(BaseModel):
    """A single image patch/tile with its offset in the original image."""
    patch_id: int
    offset_y: int  # row offset in original image
    offset_x: int  # col offset in original image
    height: int
    width: int

    class Config:
        arbitrary_types_allowed = True


class MatchPoint(BaseModel):
    """A single correspondence point between two images."""
    # Pixel coordinates in the full original images
    pixel_a_x: float
    pixel_a_y: float
    pixel_b_x: float
    pixel_b_y: float
    # Lunar coordinates
    lunar_a_lat: Optional[float] = None
    lunar_a_lon: Optional[float] = None
    lunar_b_lat: Optional[float] = None
    lunar_b_lon: Optional[float] = None
    # Quality
    confidence: float  # 0.0 - 1.0


# ──────────────────────────────────────────────
# API Request / Response Models
# ──────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response after uploading two images."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    message: str = "Images uploaded successfully. Processing started."
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobStatusResponse(BaseModel):
    """Response for job status polling."""
    job_id: str
    status: JobStatus
    progress_percent: float = 0.0  # 0-100
    current_step: str = ""
    message: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class MatchResult(BaseModel):
    """A single match point in the results response."""
    match_id: int
    image_a_pixel: dict  # {"x": float, "y": float}
    image_b_pixel: dict  # {"x": float, "y": float}
    lunar_a: dict  # {"lat": float, "lon": float}
    lunar_b: dict  # {"lat": float, "lon": float}
    confidence: float


class ImageInfo(BaseModel):
    """Summary info about a processed image."""
    instrument: InstrumentType
    filename: str
    width: int
    height: int
    resolution_m: float
    bbox: dict  # {"lat_min", "lat_max", "lon_min", "lon_max"}


class ResultsResponse(BaseModel):
    """Full results payload returned to the frontend."""
    job_id: str
    status: JobStatus
    image_a: ImageInfo
    image_b: ImageInfo
    matches: list[MatchResult]
    total_matches: int
    confidence_score: float  # 0-100
    processing_time_seconds: float
    # Statistics
    stats: dict = Field(default_factory=dict)
    # {
    #   "raw_matches": int,
    #   "after_mutual_check": int,
    #   "after_ransac": int,
    #   "avg_reprojection_error": float,
    #   "spatial_spread": float,
    # }


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str = ""
    job_id: Optional[str] = None
