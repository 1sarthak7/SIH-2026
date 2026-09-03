"""
Preprocessing Utilities — shared helpers for all instrument pipelines.
"""

import numpy as np
import cv2
from typing import Optional
from loguru import logger


def normalize_to_8bit(image: np.ndarray, source_bits: int = 16) -> np.ndarray:
    """
    Normalize an image from arbitrary bit depth to 8-bit (0-255).

    Args:
        image: Input image array
        source_bits: Original bit depth (10, 12, 16, etc.)

    Returns:
        8-bit normalized image
    """
    if image.dtype == np.uint8:
        return image

    max_val = 2 ** source_bits - 1
    # Clip to expected range, then scale
    clipped = np.clip(image.astype(np.float32), 0, max_val)
    normalized = (clipped / max_val * 255.0).astype(np.uint8)
    return normalized


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 3.0,
    tile_grid_size: int = 8,
) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization.

    CLAHE divides the image into small tiles and equalizes contrast in each
    tile independently. This is far better than global histogram equalization
    for images with both deep shadows and bright highlights (common on the Moon).

    Args:
        image: 8-bit grayscale image
        clip_limit: Threshold for contrast limiting (higher = more contrast)
        tile_grid_size: Size of the tile grid for local equalization

    Returns:
        Enhanced 8-bit image
    """
    if image.dtype != np.uint8:
        image = normalize_to_8bit(image)

    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=(tile_grid_size, tile_grid_size),
    )

    if image.ndim == 2:
        return clahe.apply(image)
    elif image.ndim == 3:
        # Apply to each channel independently
        result = np.zeros_like(image)
        for i in range(image.shape[2]):
            result[:, :, i] = clahe.apply(image[:, :, i])
        return result

    return image


def extract_patches(
    image: np.ndarray,
    patch_size: int = 512,
    overlap: int = 64,
) -> list[dict]:
    """
    Slice an image into overlapping patches.

    Args:
        image: 2D grayscale image (H, W)
        patch_size: Size of each square patch
        overlap: Number of pixels to overlap between adjacent patches

    Returns:
        List of dicts: {"image": np.ndarray, "offset_y": int, "offset_x": int, "patch_id": int}
    """
    h, w = image.shape[:2]
    stride = patch_size - overlap
    patches = []
    patch_id = 0

    # Handle images smaller than patch_size
    if h <= patch_size and w <= patch_size:
        # Pad to patch_size
        padded = np.zeros((patch_size, patch_size), dtype=image.dtype)
        padded[:h, :w] = image if image.ndim == 2 else image[:, :, 0]
        patches.append({
            "image": padded,
            "offset_y": 0,
            "offset_x": 0,
            "patch_id": 0,
        })
        return patches

    for y in range(0, h - patch_size + 1, stride):
        for x in range(0, w - patch_size + 1, stride):
            patch = image[y:y + patch_size, x:x + patch_size]
            if patch.ndim == 3:
                patch = patch[:, :, 0]  # Take first channel for matching

            patches.append({
                "image": patch,
                "offset_y": y,
                "offset_x": x,
                "patch_id": patch_id,
            })
            patch_id += 1

    # Handle right edge
    if (w - patch_size) % stride != 0:
        for y in range(0, h - patch_size + 1, stride):
            patch = image[y:y + patch_size, w - patch_size:w]
            if patch.ndim == 3:
                patch = patch[:, :, 0]
            patches.append({
                "image": patch,
                "offset_y": y,
                "offset_x": w - patch_size,
                "patch_id": patch_id,
            })
            patch_id += 1

    # Handle bottom edge
    if (h - patch_size) % stride != 0:
        for x in range(0, w - patch_size + 1, stride):
            patch = image[h - patch_size:h, x:x + patch_size]
            if patch.ndim == 3:
                patch = patch[:, :, 0]
            patches.append({
                "image": patch,
                "offset_y": h - patch_size,
                "offset_x": x,
                "patch_id": patch_id,
            })
            patch_id += 1

    logger.info(f"  Extracted {len(patches)} patches ({patch_size}×{patch_size}, stride={stride})")
    return patches


def resize_to_match(
    image: np.ndarray,
    target_height: int,
    target_width: int,
) -> np.ndarray:
    """Resize an image to match target dimensions using area interpolation."""
    if image.shape[0] == target_height and image.shape[1] == target_width:
        return image

    # Use INTER_AREA for downsampling, INTER_CUBIC for upsampling
    if image.shape[0] > target_height:
        interp = cv2.INTER_AREA
    else:
        interp = cv2.INTER_CUBIC

    return cv2.resize(image, (target_width, target_height), interpolation=interp)


def ensure_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale if it's multi-channel."""
    if image.ndim == 2:
        return image
    if image.ndim == 3:
        if image.shape[0] <= 4:  # (C, H, W) format
            return image[0]  # Take first channel
        if image.shape[2] <= 4:  # (H, W, C) format
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.shape[2] == 3 else image[:, :, 0]
    return image


def save_preview(image: np.ndarray, filepath: str) -> str:
    """Save an 8-bit preview PNG for frontend display."""
    preview_path = filepath.replace(
        "." + filepath.split(".")[-1], ".preview.png"
    )
    if image.dtype != np.uint8:
        image = normalize_to_8bit(image)
    cv2.imwrite(preview_path, image)
    logger.info(f"  Saved preview: {preview_path}")
    return preview_path
