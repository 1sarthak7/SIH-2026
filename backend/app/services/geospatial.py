"""
Geospatial Mapping Service — Step 6

Converts pixel coordinates to Lunar geographic coordinates and
computes confidence scores.
"""

import numpy as np
import rasterio
from typing import Optional
from loguru import logger

from app.models.schemas import ImageMetadata, MatchPoint


def pixel_to_geo(
    pixel_coords: np.ndarray,
    metadata: ImageMetadata,
) -> np.ndarray:
    """
    Convert pixel coordinates (x, y) to geographic coordinates (lon, lat).

    Uses the affine transform from the original GeoTIFF metadata.
    For images without real geospatial data (e.g., PNGs), returns pixel-based coords.

    Args:
        pixel_coords: (N, 2) array of (x, y) pixel coordinates
        metadata: ImageMetadata with CRS and filepath

    Returns:
        (N, 2) array of (longitude, latitude)
    """
    if metadata.crs in ("UNKNOWN", "PIXEL", ""):
        # No real CRS — return scaled pixel coordinates as pseudo-geographic
        logger.debug("  No real CRS, using pixel-based coordinates")
        geo_coords = np.zeros_like(pixel_coords, dtype=np.float64)
        geo_coords[:, 0] = metadata.bbox_lon_min + pixel_coords[:, 0] * (
            (metadata.bbox_lon_max - metadata.bbox_lon_min) / metadata.width
        )
        geo_coords[:, 1] = metadata.bbox_lat_max - pixel_coords[:, 1] * (
            (metadata.bbox_lat_max - metadata.bbox_lat_min) / metadata.height
        )
        return geo_coords

    try:
        with rasterio.open(metadata.filepath) as src:
            transform = src.transform

            geo_coords = np.zeros((len(pixel_coords), 2), dtype=np.float64)
            for i, (px, py) in enumerate(pixel_coords):
                # rasterio.transform.xy converts (row, col) → (x, y)
                x, y = rasterio.transform.xy(transform, int(py), int(px))
                geo_coords[i] = [x, y]  # [lon, lat] or [easting, northing]

            return geo_coords
    except Exception as e:
        logger.warning(f"  Failed to convert coordinates: {e}")
        # Fallback to linear interpolation from bounding box
        geo_coords = np.zeros((len(pixel_coords), 2), dtype=np.float64)
        for i, (px, py) in enumerate(pixel_coords):
            lon = metadata.bbox_lon_min + (px / metadata.width) * (
                metadata.bbox_lon_max - metadata.bbox_lon_min
            )
            lat = metadata.bbox_lat_max - (py / metadata.height) * (
                metadata.bbox_lat_max - metadata.bbox_lat_min
            )
            geo_coords[i] = [lon, lat]
        return geo_coords


def compute_reprojection_errors(
    keypoints_a: np.ndarray,
    keypoints_b: np.ndarray,
    fundamental_matrix: Optional[np.ndarray],
) -> np.ndarray:
    """
    Compute Sampson distance (reprojection error) for each match.

    The Sampson distance measures how well each match agrees with the
    estimated fundamental matrix. Lower = better.

    Args:
        keypoints_a: (N, 2) keypoints in image A
        keypoints_b: (N, 2) keypoints in image B
        fundamental_matrix: 3×3 fundamental matrix (or None)

    Returns:
        (N,) array of reprojection errors (in pixels)
    """
    if fundamental_matrix is None or len(keypoints_a) == 0:
        return np.zeros(len(keypoints_a))

    F = np.array(fundamental_matrix)
    if F.shape != (3, 3):
        return np.zeros(len(keypoints_a))

    # Convert to homogeneous coordinates
    ones = np.ones((len(keypoints_a), 1))
    pts_a = np.hstack([keypoints_a, ones])  # (N, 3)
    pts_b = np.hstack([keypoints_b, ones])  # (N, 3)

    # Sampson distance: d = (b^T F a)^2 / (||Fa||^2_[1:2] + ||F^T b||^2_[1:2])
    Fa = (F @ pts_a.T).T  # (N, 3)
    Ftb = (F.T @ pts_b.T).T  # (N, 3)

    numerator = np.sum(pts_b * Fa, axis=1) ** 2
    denominator = Fa[:, 0] ** 2 + Fa[:, 1] ** 2 + Ftb[:, 0] ** 2 + Ftb[:, 1] ** 2

    errors = np.sqrt(numerator / (denominator + 1e-10))
    return errors


def compute_spatial_spread(
    keypoints: np.ndarray,
    image_width: int,
    image_height: int,
) -> float:
    """
    Compute how well-distributed the matches are across the image.

    Divides the image into a grid and measures what fraction of grid cells
    contain at least one match. Spatially spread matches = higher quality.

    Returns:
        Float in [0, 1] — 1.0 = perfect spread, 0.0 = all clustered
    """
    if len(keypoints) < 2:
        return 0.0

    grid_size = 8  # 8×8 grid
    cell_w = image_width / grid_size
    cell_h = image_height / grid_size

    occupied = set()
    for x, y in keypoints:
        gx = min(int(x / cell_w), grid_size - 1)
        gy = min(int(y / cell_h), grid_size - 1)
        occupied.add((gx, gy))

    spread = len(occupied) / (grid_size * grid_size)
    return spread


def compute_confidence_score(
    num_matches: int,
    reprojection_errors: np.ndarray,
    spatial_spread: float,
) -> float:
    """
    Compute an overall confidence score (0-100%).

    Weighted composite of:
    - Match count (40% weight): More matches = higher confidence
    - Reprojection error (35% weight): Lower error = higher confidence
    - Spatial spread (25% weight): More distributed = higher confidence

    Args:
        num_matches: Number of verified matches
        reprojection_errors: Array of per-match errors
        spatial_spread: Spatial distribution score (0-1)

    Returns:
        Confidence score (0-100)
    """
    # Match count score: saturates at 200 matches
    match_score = min(num_matches / 200.0, 1.0) * 40.0

    # Error score: lower is better, penalized above 5px
    avg_error = np.mean(reprojection_errors) if len(reprojection_errors) > 0 else 5.0
    error_score = max(1.0 - avg_error / 5.0, 0.0) * 35.0

    # Spatial spread score
    spread_score = spatial_spread * 25.0

    total = match_score + error_score + spread_score
    return round(total, 1)


def map_matches_to_coordinates(
    keypoints_a: np.ndarray,
    keypoints_b: np.ndarray,
    confidence: np.ndarray,
    metadata_a: ImageMetadata,
    metadata_b: ImageMetadata,
    verification_stats: dict,
) -> tuple[list[MatchPoint], float, dict]:
    """
    Full geospatial mapping pipeline:
    1. Convert pixel → lunar coordinates for both images
    2. Compute reprojection errors
    3. Compute spatial spread
    4. Calculate confidence score

    Returns:
        - matches: List of MatchPoint objects with pixel + lunar coords
        - confidence_score: Overall confidence (0-100)
        - stats: Processing statistics
    """
    logger.info(f"Mapping {len(keypoints_a)} matches to lunar coordinates...")

    if len(keypoints_a) == 0:
        return [], 0.0, {"error": "No matches to map"}

    # Step 1: Convert pixel → geographic coordinates
    geo_a = pixel_to_geo(keypoints_a, metadata_a)
    geo_b = pixel_to_geo(keypoints_b, metadata_b)

    # Step 2: Compute reprojection errors
    F = verification_stats.get("fundamental_matrix")
    if F is not None:
        F = np.array(F)
    reproj_errors = compute_reprojection_errors(keypoints_a, keypoints_b, F)

    # Step 3: Compute spatial spread
    spread_a = compute_spatial_spread(keypoints_a, metadata_a.width, metadata_a.height)
    spread_b = compute_spatial_spread(keypoints_b, metadata_b.width, metadata_b.height)
    spatial_spread = (spread_a + spread_b) / 2.0

    # Step 4: Confidence score
    confidence_score = compute_confidence_score(len(keypoints_a), reproj_errors, spatial_spread)

    # Step 5: Build MatchPoint objects
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
        "spatial_spread_a": float(spread_a),
        "spatial_spread_b": float(spread_b),
        "spatial_spread_avg": float(spatial_spread),
    }

    logger.info(
        f"  Confidence: {confidence_score}% | "
        f"Avg error: {stats['avg_reprojection_error']:.2f}px | "
        f"Spread: {spatial_spread:.2f}"
    )

    return matches, confidence_score, stats
