"""
Preprocessing Service — Step 2

Instrument-specific preprocessing pipelines for OHRC, TMC, and IIRS images.
Each pipeline normalizes the raw data and produces standardized patches
ready for feature extraction.
"""

import numpy as np
from sklearn.decomposition import PCA
from loguru import logger

from app.core.config import settings
from app.models.schemas import ImageMetadata, InstrumentType
from app.services.preprocessing_utils import (
    normalize_to_8bit,
    apply_clahe,
    extract_patches,
    ensure_grayscale,
    save_preview,
)


def preprocess_ohrc(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    OHRC Preprocessing Pipeline:
    1. Convert 10-bit to 8-bit
    2. Apply CLAHE for shadow/highlight recovery
    3. Tile into overlapping 512×512 patches

    Args:
        pixel_data: Raw OHRC image (typically 10-bit stored as uint16)
        metadata: Image metadata

    Returns:
        - patches: List of patch dicts with 'image', 'offset_y', 'offset_x'
        - full_processed: The full preprocessed image (for preview/visualization)
    """
    logger.info("Preprocessing OHRC image...")

    # Step 1: Ensure grayscale
    image = ensure_grayscale(pixel_data)

    # Step 2: Convert to 8-bit (OHRC is 10-bit: 0-1023)
    if image.dtype in (np.uint16, np.int16, np.float32, np.float64):
        image = normalize_to_8bit(image, source_bits=10)
    elif image.dtype != np.uint8:
        image = normalize_to_8bit(image)

    logger.info(f"  Converted to 8-bit: shape={image.shape}, range=[{image.min()}, {image.max()}]")

    # Step 3: CLAHE — recovers detail in both shadows and highlights
    image = apply_clahe(
        image,
        clip_limit=settings.CLAHE_CLIP_LIMIT,
        tile_grid_size=settings.CLAHE_TILE_GRID,
    )

    logger.info(f"  CLAHE applied: range=[{image.min()}, {image.max()}]")

    # Step 4: Save preview for frontend
    save_preview(image, metadata.filepath)

    # Step 5: Extract patches
    patches = extract_patches(
        image,
        patch_size=settings.PATCH_SIZE,
        overlap=settings.PATCH_OVERLAP,
    )

    return patches, image


def preprocess_tmc(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    TMC-2 Preprocessing Pipeline:
    1. Ensure grayscale
    2. Normalize to 8-bit
    3. Apply contrast enhancement (CLAHE)
    4. Tile into patches

    TMC-2 has lower resolution than OHRC (5m vs 0.25m) but wider coverage.
    It may have 3 bands (stereo triplet) — we use the nadir view.

    Args:
        pixel_data: Raw TMC image
        metadata: Image metadata

    Returns:
        - patches: List of patch dicts
        - full_processed: Full preprocessed image
    """
    logger.info("Preprocessing TMC image...")

    # Step 1: Handle multi-band (TMC stereo has fore/nadir/aft views)
    if pixel_data.ndim == 3:
        if pixel_data.shape[0] <= 4:  # (bands, H, W)
            # Use nadir view (middle band) if stereo triplet
            if pixel_data.shape[0] == 3:
                image = pixel_data[1]  # Nadir
                logger.info("  Using nadir band from stereo triplet")
            else:
                image = pixel_data[0]
        else:
            image = ensure_grayscale(pixel_data)
    else:
        image = pixel_data

    # Step 2: Normalize to 8-bit
    if image.dtype != np.uint8:
        image = normalize_to_8bit(image, source_bits=16)

    # Step 3: CLAHE
    image = apply_clahe(image, clip_limit=2.5, tile_grid_size=8)

    logger.info(f"  Processed: shape={image.shape}, range=[{image.min()}, {image.max()}]")

    # Step 4: Save preview
    save_preview(image, metadata.filepath)

    # Step 5: Extract patches
    patches = extract_patches(
        image,
        patch_size=settings.PATCH_SIZE,
        overlap=settings.PATCH_OVERLAP,
    )

    return patches, image


def preprocess_iirs(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    IIRS Preprocessing Pipeline:
    1. Apply PCA to reduce 256 spectral bands to 3 spatial components
    2. Normalize to 8-bit
    3. Apply CLAHE to first principal component
    4. Tile into patches

    IIRS captures 256 spectral bands — far too many for spatial matching.
    PCA compresses this into 3 components that capture 95%+ of spatial variance.

    Args:
        pixel_data: Raw IIRS hyperspectral cube (bands, H, W)
        metadata: Image metadata

    Returns:
        - patches: List of patch dicts (using first principal component)
        - full_processed: Full PCA-compressed image
    """
    logger.info("Preprocessing IIRS hyperspectral image...")

    if pixel_data.ndim == 2:
        # Already single-band — treat like TMC
        logger.warning("  IIRS image appears to be single-band, treating as grayscale")
        return preprocess_tmc(pixel_data, metadata)

    # pixel_data shape: (bands, H, W) or (H, W, bands)
    if pixel_data.ndim == 3:
        if pixel_data.shape[0] > pixel_data.shape[2]:
            # (H, W, bands) format — transpose to (bands, H, W)
            pixel_data = np.transpose(pixel_data, (2, 0, 1))

    bands, h, w = pixel_data.shape
    logger.info(f"  Hyperspectral cube: {bands} bands × {h}×{w}")

    # Step 1: Reshape for PCA — each pixel becomes a spectral vector
    pixels = pixel_data.reshape(bands, -1).T.astype(np.float32)  # (H*W, bands)

    # Handle NaN/inf values
    pixels = np.nan_to_num(pixels, nan=0.0, posinf=0.0, neginf=0.0)

    # Step 2: PCA — compress spectral dimension
    n_components = min(settings.PCA_N_COMPONENTS, bands)
    pca = PCA(n_components=n_components)
    compressed = pca.fit_transform(pixels)  # (H*W, n_components)

    explained_var = sum(pca.explained_variance_ratio_) * 100
    logger.info(f"  PCA: {bands} bands → {n_components} components ({explained_var:.1f}% variance explained)")

    # Step 3: Reshape back to spatial image
    pca_image = compressed.reshape(h, w, n_components)

    # Step 4: Use first principal component for matching (highest spatial info)
    spatial_image = pca_image[:, :, 0]

    # Step 5: Normalize to 8-bit
    spatial_image = ((spatial_image - spatial_image.min()) /
                     (spatial_image.max() - spatial_image.min() + 1e-8) * 255).astype(np.uint8)

    # Step 6: CLAHE
    spatial_image = apply_clahe(spatial_image, clip_limit=3.0, tile_grid_size=8)

    # Step 7: Save preview
    save_preview(spatial_image, metadata.filepath)

    # Step 8: Extract patches
    patches = extract_patches(
        spatial_image,
        patch_size=settings.PATCH_SIZE,
        overlap=settings.PATCH_OVERLAP,
    )

    return patches, spatial_image


def preprocess_image(
    pixel_data: np.ndarray,
    metadata: ImageMetadata,
) -> tuple[list[dict], np.ndarray]:
    """
    Main preprocessing entry point. Routes to instrument-specific pipeline.

    Args:
        pixel_data: Raw image data
        metadata: Image metadata with instrument type

    Returns:
        - patches: List of preprocessed patch dicts
        - full_processed: Full preprocessed image
    """
    instrument = metadata.instrument

    if instrument == InstrumentType.OHRC:
        return preprocess_ohrc(pixel_data, metadata)
    elif instrument == InstrumentType.TMC:
        return preprocess_tmc(pixel_data, metadata)
    elif instrument == InstrumentType.IIRS:
        return preprocess_iirs(pixel_data, metadata)
    else:
        # Default: treat as generic grayscale
        logger.warning(f"Unknown instrument '{instrument}', using generic preprocessing")
        image = ensure_grayscale(pixel_data)
        if image.dtype != np.uint8:
            image = normalize_to_8bit(image)
        image = apply_clahe(image)
        save_preview(image, metadata.filepath)
        patches = extract_patches(image, settings.PATCH_SIZE, settings.PATCH_OVERLAP)
        return patches, image
