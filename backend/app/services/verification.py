"""
Geometric Verification Service — Step 5

Filters raw LoFTR matches using:
1. Mutual Nearest Neighbor (MNN) check
2. MAGSAC++ geometric verification via OpenCV
"""

import numpy as np
import cv2
from loguru import logger

from app.core.config import settings


def mutual_nearest_neighbor_check(
    keypoints_a: np.ndarray,
    keypoints_b: np.ndarray,
    confidence: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Enforce mutual nearest neighbor consistency.

    A match (A_i → B_j) is valid only if B_j's best match is also A_i.
    This eliminates many-to-one and one-to-many matches.

    Note: LoFTR already enforces soft mutual matching via dual-softmax,
    but this hard check catches any remaining inconsistencies.
    """
    if len(keypoints_a) == 0:
        return keypoints_a, keypoints_b, confidence

    # Build spatial distance matrix between all B keypoints
    # For each B point, find the A point that maps to the nearest B point
    from scipy.spatial import cKDTree

    tree_b = cKDTree(keypoints_b)

    # For each match, check if it's mutually closest
    valid_mask = np.ones(len(keypoints_a), dtype=bool)

    # Group matches by their B-point indices
    # If multiple A points map to the same B point, keep only the highest-confidence one
    b_to_best_a = {}  # Maps B-point index → (confidence, A-index)

    for idx in range(len(keypoints_a)):
        # Find nearest B point to this match's B point
        b_point = tuple(keypoints_b[idx].round(2))

        if b_point in b_to_best_a:
            if confidence[idx] > b_to_best_a[b_point][0]:
                # This match is better — invalidate the previous one
                valid_mask[b_to_best_a[b_point][1]] = False
                b_to_best_a[b_point] = (confidence[idx], idx)
            else:
                # Previous match was better — invalidate this one
                valid_mask[idx] = False
        else:
            b_to_best_a[b_point] = (confidence[idx], idx)

    # Similarly for A points
    a_to_best_b = {}
    for idx in range(len(keypoints_a)):
        if not valid_mask[idx]:
            continue
        a_point = tuple(keypoints_a[idx].round(2))

        if a_point in a_to_best_b:
            if confidence[idx] > a_to_best_b[a_point][0]:
                valid_mask[a_to_best_b[a_point][1]] = False
                a_to_best_b[a_point] = (confidence[idx], idx)
            else:
                valid_mask[idx] = False
        else:
            a_to_best_b[a_point] = (confidence[idx], idx)

    removed = (~valid_mask).sum()
    if removed > 0:
        logger.info(f"  MNN check: removed {removed} non-mutual matches")

    return keypoints_a[valid_mask], keypoints_b[valid_mask], confidence[valid_mask]


def geometric_verification(
    keypoints_a: np.ndarray,
    keypoints_b: np.ndarray,
    confidence: np.ndarray,
    method: str = "magsac",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """
    Apply MAGSAC++ geometric verification to filter outlier matches.

    MAGSAC++ estimates the fundamental matrix (the geometric relationship
    between two views) and discards matches that are inconsistent with it.

    Args:
        keypoints_a: (N, 2) keypoint coordinates in image A
        keypoints_b: (N, 2) keypoint coordinates in image B
        confidence: (N,) confidence scores
        method: "magsac" (default), "ransac", or "lmeds"

    Returns:
        - filtered keypoints_a
        - filtered keypoints_b
        - filtered confidence
        - stats dict with verification metrics
    """
    stats = {
        "input_matches": len(keypoints_a),
        "method": method,
        "fundamental_matrix": None,
        "inlier_ratio": 0.0,
    }

    if len(keypoints_a) < 8:
        logger.warning(f"  Only {len(keypoints_a)} matches — need ≥8 for geometric verification")
        stats["output_matches"] = len(keypoints_a)
        return keypoints_a, keypoints_b, confidence, stats

    # Select OpenCV method
    cv_methods = {
        "magsac": cv2.USAC_MAGSAC,
        "ransac": cv2.RANSAC,
        "lmeds": cv2.LMEDS,
    }
    cv_method = cv_methods.get(method, cv2.USAC_MAGSAC)

    # Run fundamental matrix estimation with MAGSAC++
    F, inlier_mask = cv2.findFundamentalMat(
        keypoints_a.astype(np.float64),
        keypoints_b.astype(np.float64),
        method=cv_method,
        ransacReprojThreshold=settings.RANSAC_REPROJ_THRESHOLD,
        confidence=settings.RANSAC_CONFIDENCE,
        maxIters=settings.RANSAC_MAX_ITERS,
    )

    if inlier_mask is None:
        logger.warning("  MAGSAC++ failed to find a valid fundamental matrix")
        stats["output_matches"] = len(keypoints_a)
        return keypoints_a, keypoints_b, confidence, stats

    inlier_mask = inlier_mask.ravel().astype(bool)
    inlier_ratio = inlier_mask.sum() / len(inlier_mask)

    stats["fundamental_matrix"] = F.tolist() if F is not None else None
    stats["inlier_ratio"] = float(inlier_ratio)
    stats["output_matches"] = int(inlier_mask.sum())

    logger.info(
        f"  MAGSAC++: {inlier_mask.sum()}/{len(inlier_mask)} inliers "
        f"({inlier_ratio:.1%} inlier ratio)"
    )

    return (
        keypoints_a[inlier_mask],
        keypoints_b[inlier_mask],
        confidence[inlier_mask],
        stats,
    )


def verify_matches(
    raw_matches: list[dict],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """
    Full verification pipeline: aggregate patch matches → MNN → MAGSAC++

    Args:
        raw_matches: List of match dicts from FeatureMatcher.match_patches()

    Returns:
        - keypoints_a: (N, 2) verified coordinates in image A
        - keypoints_b: (N, 2) verified coordinates in image B
        - confidence: (N,) confidence scores
        - stats: Verification statistics
    """
    if not raw_matches:
        return np.array([]), np.array([]), np.array([]), {"error": "No matches to verify"}

    # Aggregate all matches from all patch pairs
    all_kpts_a = np.vstack([m["keypoints_a"] for m in raw_matches])
    all_kpts_b = np.vstack([m["keypoints_b"] for m in raw_matches])
    all_conf = np.concatenate([m["confidence"] for m in raw_matches])

    logger.info(f"Verification pipeline: {len(all_kpts_a)} raw matches")

    stats = {"raw_matches": len(all_kpts_a)}

    # Step 1: Mutual Nearest Neighbor check
    kpts_a, kpts_b, conf = mutual_nearest_neighbor_check(all_kpts_a, all_kpts_b, all_conf)
    stats["after_mutual_check"] = len(kpts_a)

    # Step 2: MAGSAC++ geometric verification
    kpts_a, kpts_b, conf, geo_stats = geometric_verification(kpts_a, kpts_b, conf)
    stats.update(geo_stats)
    stats["after_ransac"] = len(kpts_a)

    logger.info(
        f"Verification complete: {stats['raw_matches']} → "
        f"{stats['after_mutual_check']} (MNN) → "
        f"{stats['after_ransac']} (MAGSAC++)"
    )

    return kpts_a, kpts_b, conf, stats
