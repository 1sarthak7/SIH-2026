"""
Processing Pipeline Orchestrator — The Main Brain

Chains all processing steps together:
1. Ingestion → 2. Preprocessing → 3. Matching → 4. Verification → 5. Geospatial Mapping

This module is called by the upload endpoint as a background task.
"""

import time
from typing import Callable, Optional

import numpy as np
from loguru import logger

from app.models.schemas import (
    JobStatus,
    ImageMetadata,
    ResultsResponse,
    ImageInfo,
    MatchResult,
)
from app.services.ingestion import ingest_image
from app.services.preprocessing import preprocess_image
from app.services.matching import FeatureMatcher
from app.services.verification import verify_matches
from app.services.geospatial import map_matches_to_coordinates


# Singleton matcher (loaded once, reused across jobs)
_matcher: Optional[FeatureMatcher] = None


def get_matcher() -> FeatureMatcher:
    """Get or create the singleton FeatureMatcher (avoids reloading model per job)."""
    global _matcher
    if _matcher is None:
        _matcher = FeatureMatcher()
    return _matcher


class ProcessingPipeline:
    """
    End-to-end processing pipeline for image correspondence.

    Orchestrates all 6 steps and reports progress via a callback function.
    """

    def __init__(self):
        self.matcher = get_matcher()

    async def run(
        self,
        path_a: str,
        path_b: str,
        progress_callback: Optional[Callable] = None,
    ) -> ResultsResponse:
        """
        Run the full pipeline on two images.

        Args:
            path_a: Path to first image file
            path_b: Path to second image file
            progress_callback: Optional function(status, progress, step, message)

        Returns:
            ResultsResponse with all match data
        """
        start_time = time.time()

        def report(status: JobStatus, progress: float, step: str, message: str):
            if progress_callback:
                progress_callback(status, progress, step, message)
            logger.info(f"[{progress:.0f}%] {step}: {message}")

        # ──────────────────────────────────────
        # Step 1: Ingestion
        # ──────────────────────────────────────
        report(JobStatus.INGESTING, 5, "Ingestion", "Parsing image files...")

        pixel_a, meta_a = ingest_image(path_a)
        pixel_b, meta_b = ingest_image(path_b)

        report(
            JobStatus.INGESTING, 15, "Ingestion",
            f"Loaded {meta_a.instrument.value.upper()} ({meta_a.width}×{meta_a.height}) "
            f"and {meta_b.instrument.value.upper()} ({meta_b.width}×{meta_b.height})"
        )

        # ──────────────────────────────────────
        # Step 2: Preprocessing
        # ──────────────────────────────────────
        report(JobStatus.PREPROCESSING, 20, "Preprocessing", f"Processing {meta_a.instrument.value.upper()} image...")
        patches_a, processed_a = preprocess_image(pixel_a, meta_a)

        report(JobStatus.PREPROCESSING, 30, "Preprocessing", f"Processing {meta_b.instrument.value.upper()} image...")
        patches_b, processed_b = preprocess_image(pixel_b, meta_b)

        report(
            JobStatus.PREPROCESSING, 40, "Preprocessing",
            f"Created {len(patches_a)} + {len(patches_b)} patches"
        )

        # ──────────────────────────────────────
        # Step 3 & 4: Feature Matching (LoFTR)
        # ──────────────────────────────────────
        report(JobStatus.MATCHING, 45, "Feature Matching", "Running LoFTR deep matching...")

        raw_matches = self.matcher.match_patches(patches_a, patches_b)

        total_raw = sum(m["confidence"].shape[0] for m in raw_matches) if raw_matches else 0
        report(
            JobStatus.MATCHING, 65, "Feature Matching",
            f"Found {total_raw} raw correspondences"
        )

        # ──────────────────────────────────────
        # Step 5: Verification
        # ──────────────────────────────────────
        report(JobStatus.VERIFYING, 70, "Verification", "Running MNN + MAGSAC++ filtering...")

        kpts_a, kpts_b, confidence, verify_stats = verify_matches(raw_matches)

        report(
            JobStatus.VERIFYING, 80, "Verification",
            f"Verified {len(kpts_a)} matches (from {total_raw} raw)"
        )

        # ──────────────────────────────────────
        # Step 6: Geospatial Mapping
        # ──────────────────────────────────────
        report(JobStatus.MAPPING, 85, "Geospatial Mapping", "Converting to lunar coordinates...")

        match_points, confidence_score, geo_stats = map_matches_to_coordinates(
            kpts_a, kpts_b, confidence, meta_a, meta_b, verify_stats
        )

        # ──────────────────────────────────────
        # Build Response
        # ──────────────────────────────────────
        elapsed = time.time() - start_time

        # Convert MatchPoints to MatchResults for API response
        match_results = [
            MatchResult(
                match_id=i,
                image_a_pixel={"x": mp.pixel_a_x, "y": mp.pixel_a_y},
                image_b_pixel={"x": mp.pixel_b_x, "y": mp.pixel_b_y},
                lunar_a={"lat": mp.lunar_a_lat or 0.0, "lon": mp.lunar_a_lon or 0.0},
                lunar_b={"lat": mp.lunar_b_lat or 0.0, "lon": mp.lunar_b_lon or 0.0},
                confidence=mp.confidence,
            )
            for i, mp in enumerate(match_points)
        ]

        result = ResultsResponse(
            job_id="",  # Will be set by the caller
            status=JobStatus.COMPLETED,
            image_a=ImageInfo(
                instrument=meta_a.instrument,
                filename=meta_a.filepath.split("/")[-1],
                width=meta_a.width,
                height=meta_a.height,
                resolution_m=meta_a.resolution_m,
                bbox={
                    "lat_min": meta_a.bbox_lat_min,
                    "lat_max": meta_a.bbox_lat_max,
                    "lon_min": meta_a.bbox_lon_min,
                    "lon_max": meta_a.bbox_lon_max,
                },
            ),
            image_b=ImageInfo(
                instrument=meta_b.instrument,
                filename=meta_b.filepath.split("/")[-1],
                width=meta_b.width,
                height=meta_b.height,
                resolution_m=meta_b.resolution_m,
                bbox={
                    "lat_min": meta_b.bbox_lat_min,
                    "lat_max": meta_b.bbox_lat_max,
                    "lon_min": meta_b.bbox_lon_min,
                    "lon_max": meta_b.bbox_lon_max,
                },
            ),
            matches=match_results,
            total_matches=len(match_results),
            confidence_score=confidence_score,
            processing_time_seconds=round(elapsed, 2),
            stats={**verify_stats, **geo_stats},
        )

        report(
            JobStatus.COMPLETED, 100, "Complete",
            f"Done! {len(match_results)} matches, {confidence_score}% confidence, {elapsed:.1f}s"
        )

        return result
