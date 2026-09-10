"""
Geospatial Mapping Service — Step 6 (Updated for ISRO geometry CSV)

Uses the per-pixel geometry grid from ISRO PRADAN for accurate
Lunar coordinate mapping, with fallback to bounding box interpolation.
"""

import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from typing import Optional
from loguru import logger

from app.models.schemas import ImageMetadata, MatchPoint


class GeometryMapper:
    """
    Maps pixel coordinates to Lunar lat/lon using ISRO geometry CSV data.
    
    The geometry CSV provides (Longitude, Latitude, Pixel, Scan) samples
    every ~100 pixels. We interpolate between these samples for sub-grid accuracy.
    """

    def __init__(self, geometry_df: Optional[pd.DataFrame] = None, metadata: Optional[ImageMetadata] = None):
        self.geometry_df = geometry_df
        self.metadata = metadata
        self._interpolator_lon = None
        self._interpolator_lat = None

        if geometry_df is not None and len(geometry_df) > 0:
            self._build_interpolator()

    def _build_interpolator(self):
        """Pre-compute interpolation grid from geometry CSV."""
        df = self.geometry_df
        
        # CSV columns: Longitude, Latitude, Pixel, Scan
        points = df[["Pixel", "Scan"]].values  # (x, y) in pixel space
        lons = df["Longitude"].values
        lats = df["Latitude"].values

        self._grid_points = points
        self._grid_lons = lons
        self._grid_lats = lats

        logger.info(
            f"  Built geometry interpolator from {len(df)} control points "
            f"(lat: {lats.min():.4f} to {lats.max():.4f}, "
            f"lon: {lons.min():.4f} to {lons.max():.4f})"
        )

    def pixel_to_lunar(self, pixel_coords: np.ndarray) -> np.ndarray:
        """
        Convert pixel (x, y) to Lunar (lon, lat).

        Args:
            pixel_coords: (N, 2) array of (x, y) pixel coordinates

        Returns:
            (N, 2) array of (longitude, latitude)
        """
        if len(pixel_coords) == 0:
            return np.array([]).reshape(0, 2)

        if self._grid_points is not None:
            return self._interpolate(pixel_coords)
        elif self.metadata:
            return self._bbox_fallback(pixel_coords)
        else:
            return pixel_coords.astype(np.float64)

    def _interpolate(self, pixel_coords: np.ndarray) -> np.ndarray:
        """Interpolate coordinates using the geometry grid."""
        try:
            lons = griddata(
                self._grid_points, self._grid_lons,
                pixel_coords, method="linear", fill_value=np.nan
            )
            lats = griddata(
                self._grid_points, self._grid_lats,
                pixel_coords, method="linear", fill_value=np.nan
            )

            # Fill NaN values with nearest neighbor
            nan_mask = np.isnan(lons) | np.isnan(lats)
            if nan_mask.any():
                lons_nn = griddata(
                    self._grid_points, self._grid_lons,
                    pixel_coords[nan_mask], method="nearest"
                )
                lats_nn = griddata(
                    self._grid_points, self._grid_lats,
                    pixel_coords[nan_mask], method="nearest"
                )
                lons[nan_mask] = lons_nn
                lats[nan_mask] = lats_nn

            return np.column_stack([lons, lats])
        except Exception as e:
            logger.warning(f"Interpolation failed: {e}, using bbox fallback")
            return self._bbox_fallback(pixel_coords)

    def _bbox_fallback(self, pixel_coords: np.ndarray) -> np.ndarray:
        """Linear interpolation from bounding box corners."""
        m = self.metadata
        geo = np.zeros((len(pixel_coords), 2), dtype=np.float64)
        for i, (px, py) in enumerate(pixel_coords):
            lon = m.bbox_lon_min + (px / m.width) * (m.bbox_lon_max - m.bbox_lon_min)
            lat = m.bbox_lat_max - (py / m.height) * (m.bbox_lat_max - m.bbox_lat_min)
            geo[i] = [lon, lat]
        return geo


def compute_reprojection_errors(
    keypoints_a: np.ndarray,
    keypoints_b: np.ndarray,
    fundamental_matrix: Optional[np.ndarray],
) -> np.ndarray:
    """Compute Sampson distance for each match pair."""
    if fundamental_matrix is None or len(keypoints_a) == 0:
        return np.zeros(len(keypoints_a))

    F = np.array(fundamental_matrix)
    if F.shape != (3, 3):
        return np.zeros(len(keypoints_a))

    ones = np.ones((len(keypoints_a), 1))
    pts_a = np.hstack([keypoints_a, ones])
    pts_b = np.hstack([keypoints_b, ones])

    Fa = (F @ pts_a.T).T
    Ftb = (F.T @ pts_b.T).T

    numerator = np.sum(pts_b * Fa, axis=1) ** 2
    denominator = Fa[:, 0] ** 2 + Fa[:, 1] ** 2 + Ftb[:, 0] ** 2 + Ftb[:, 1] ** 2

    return np.sqrt(numerator / (denominator + 1e-10))


def compute_spatial_spread(keypoints: np.ndarray, width: int, height: int) -> float:
    """Compute match distribution across an 8×8 grid."""
    if len(keypoints) < 2:
        return 0.0
    grid = 8
    occupied = set()
    for x, y in keypoints:
        gx = min(int(x / (width / grid)), grid - 1)
        gy = min(int(y / (height / grid)), grid - 1)
        occupied.add((gx, gy))
    return len(occupied) / (grid * grid)


def compute_confidence_score(num_matches: int, reproj_errors: np.ndarray, spread: float) -> float:
    """Composite confidence score (0-100%)."""
    match_score = min(num_matches / 200.0, 1.0) * 40.0
    avg_err = np.mean(reproj_errors) if len(reproj_errors) > 0 else 5.0
    error_score = max(1.0 - avg_err / 5.0, 0.0) * 35.0
    spread_score = spread * 25.0
    return round(match_score + error_score + spread_score, 1)


def map_matches_to_coordinates(
    keypoints_a: np.ndarray,
    keypoints_b: np.ndarray,
    confidence: np.ndarray,
    metadata_a: ImageMetadata,
    metadata_b: ImageMetadata,
    verification_stats: dict,
    geometry_a: Optional[pd.DataFrame] = None,
    geometry_b: Optional[pd.DataFrame] = None,
) -> tuple[list[MatchPoint], float, dict]:
    """
    Full geospatial mapping pipeline using ISRO geometry data.
    """
    logger.info(f"Mapping {len(keypoints_a)} matches to lunar coordinates...")

    if len(keypoints_a) == 0:
        return [], 0.0, {"error": "No matches to map"}

    # Build mappers (prefer geometry CSV, fall back to bbox)
    mapper_a = GeometryMapper(geometry_a, metadata_a)
    mapper_b = GeometryMapper(geometry_b, metadata_b)

    # Convert pixel → lunar
    geo_a = mapper_a.pixel_to_lunar(keypoints_a)
    geo_b = mapper_b.pixel_to_lunar(keypoints_b)

    # Reprojection errors
    F = verification_stats.get("fundamental_matrix")
    if F is not None:
        F = np.array(F)
    reproj_errors = compute_reprojection_errors(keypoints_a, keypoints_b, F)

    # Spatial spread
    spread_a = compute_spatial_spread(keypoints_a, metadata_a.width, metadata_a.height)
    spread_b = compute_spatial_spread(keypoints_b, metadata_b.width, metadata_b.height)
    spread = (spread_a + spread_b) / 2.0

    # Confidence
    score = compute_confidence_score(len(keypoints_a), reproj_errors, spread)

    # Build match points
    matches = []
    for i in range(len(keypoints_a)):
        matches.append(MatchPoint(
            pixel_a_x=float(keypoints_a[i, 0]),
            pixel_a_y=float(keypoints_a[i, 1]),
            pixel_b_x=float(keypoints_b[i, 0]),
            pixel_b_y=float(keypoints_b[i, 1]),
            lunar_a_lon=float(geo_a[i, 0]),
            lunar_a_lat=float(geo_a[i, 1]),
            lunar_b_lon=float(geo_b[i, 0]),
            lunar_b_lat=float(geo_b[i, 1]),
            confidence=float(confidence[i]),
        ))

    stats = {
        "avg_reprojection_error": float(np.mean(reproj_errors)),
        "max_reprojection_error": float(np.max(reproj_errors)) if len(reproj_errors) > 0 else 0.0,
        "spatial_spread_avg": float(spread),
        "coordinate_source_a": "geometry_csv" if geometry_a is not None else "bbox_interpolation",
        "coordinate_source_b": "geometry_csv" if geometry_b is not None else "bbox_interpolation",
    }

    logger.info(f"  ✅ Confidence: {score}% | Avg error: {stats['avg_reprojection_error']:.2f}px")

    return matches, score, stats
