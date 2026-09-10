"""
Preprocessing Service — Step 2 (Optimized)

Instrument-specific preprocessing pipelines for OHRC, TMC, and IIRS images.
Now with intelligent downsampling and smart patch selection to run in 2-3 min
instead of 30+ min on massive ISRO images.
"""

import numpy as np
import cv2
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

# Maximum dimension for processing (downsample if larger)
MAX_PROCESSING_DIM = 4096
MAX_PATCHES = 40  # Limit total patches per image


def _smart_downsample(image: np.ndarray, max_dim: int = MAX_PROCESSING_DIM) -> tuple[np.ndarray, float]:
    """
    Downsample image if it's too large for efficient processing.
    
    Returns:
        - downsampled image
        - scale factor (for mapping coordinates back)
    """
    h, w = image.shape[:2]
    max_side = max(h, w)

    if max_side <= max_dim:
        return image, 1.0

    scale = max_dim / max_side
    new_h = int(h * scale)
    new_w = int(w * scale)

    logger.info(f"  Downsampling: {w}×{h} → {new_w}×{new_h} (scale={scale:.4f})")
    downsampled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return downsampled, scale


def _select_informative_patches(patches: list[dict], max_patches: int = MAX_PATCHES) -> list[dict]:
    """
    Select the most informative patches based on texture content.
    
    Ranks patches by their Laplacian variance (texture/edge density).
    Blank/uniform patches are discarded. This is critical for LoFTR
    which needs texture to find features.
    """
    if len(patches) <= max_patches:
        return patches

    scored = []
    for p in patches:
        img = p["image"]
        # Laplacian variance = measure of texture/edges
        laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
        # Also check standard deviation (reject very uniform patches)
        std = np.std(img.astype(np.float32))
        
        # Skip nearly uniform patches (crater shadows, space, etc.)
        if std < 5.0:
            continue
            
        scored.append((laplacian_var, p))

    # Sort by texture content (highest first)
    scored.sort(key=lambda x: x[0], reverse=True)
    
    selected = [p for _, p in scored[:max_patches]]
    
    logger.info(
        f"  Smart selection: {len(patches)} patches → {len(selected)} "
        f"(dropped {len(patches) - len(scored)} uniform, kept top {len(selected)} by texture)"
    )
    
    return selected


def preprocess_ohrc(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    OHRC Preprocessing Pipeline:
    1. Ensure grayscale
    2. Convert to 8-bit if needed
    3. Downsample for processing efficiency
    4. Apply CLAHE for shadow/highlight recovery
    5. Extract patches with smart selection
    """
    logger.info("Preprocessing OHRC image...")

    image = ensure_grayscale(pixel_data)

    # OHRC from PRADAN is already 8-bit (UnsignedByte)
    if image.dtype in (np.uint16, np.int16, np.float32, np.float64):
        image = normalize_to_8bit(image, source_bits=10)
    elif image.dtype != np.uint8:
        image = normalize_to_8bit(image)

    logger.info(f"  8-bit: shape={image.shape}, range=[{image.min()}, {image.max()}]")

    # Downsample large images
    image, scale = _smart_downsample(image)
    
    # Store scale factor in metadata for coordinate mapping
    metadata._preprocessing_scale = scale

    # CLAHE
    image = apply_clahe(
        image,
        clip_limit=settings.CLAHE_CLIP_LIMIT,
        tile_grid_size=settings.CLAHE_TILE_GRID,
    )
    logger.info(f"  CLAHE applied: range=[{image.min()}, {image.max()}]")

    # Save preview
    save_preview(image, metadata.filepath)

    # Extract patches + smart selection
    patches = extract_patches(image, patch_size=settings.PATCH_SIZE, overlap=settings.PATCH_OVERLAP)
    patches = _select_informative_patches(patches, MAX_PATCHES)

    return patches, image


def preprocess_tmc(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    TMC-2 Preprocessing Pipeline:
    1. Handle multi-band / 16-bit data
    2. Downsample
    3. CLAHE
    4. Smart patch extraction
    """
    logger.info("Preprocessing TMC image...")

    # Handle multi-band (TMC stereo has fore/nadir/aft)
    if pixel_data.ndim == 3:
        if pixel_data.shape[0] <= 4:
            image = pixel_data[1] if pixel_data.shape[0] == 3 else pixel_data[0]
            logger.info("  Using nadir band from stereo triplet")
        else:
            image = ensure_grayscale(pixel_data)
    else:
        image = pixel_data

    # TMC from PRADAN is 16-bit (UnsignedLSB2)
    if image.dtype != np.uint8:
        image = normalize_to_8bit(image, source_bits=16)

    logger.info(f"  8-bit: shape={image.shape}, range=[{image.min()}, {image.max()}]")

    # Downsample
    image, scale = _smart_downsample(image)
    metadata._preprocessing_scale = scale

    # CLAHE
    image = apply_clahe(image, clip_limit=2.5, tile_grid_size=8)
    logger.info(f"  Processed: shape={image.shape}, range=[{image.min()}, {image.max()}]")

    # Save preview
    save_preview(image, metadata.filepath)

    # Extract patches + smart selection
    patches = extract_patches(image, patch_size=settings.PATCH_SIZE, overlap=settings.PATCH_OVERLAP)
    patches = _select_informative_patches(patches, MAX_PATCHES)

    return patches, image


def preprocess_iirs(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    IIRS Preprocessing Pipeline:
    1. PCA: 256 bands → 3 components
    2. Use first PC for spatial matching
    3. CLAHE + smart patching
    """
    logger.info("Preprocessing IIRS hyperspectral image...")

    if pixel_data.ndim == 2:
        logger.warning("  Single-band IIRS, treating as grayscale")
        return preprocess_tmc(pixel_data, metadata)

    if pixel_data.ndim == 3:
        if pixel_data.shape[0] > pixel_data.shape[2]:
            pixel_data = np.transpose(pixel_data, (2, 0, 1))

    bands, h, w = pixel_data.shape
    logger.info(f"  Hyperspectral cube: {bands} bands × {h}×{w}")

    pixels = pixel_data.reshape(bands, -1).T.astype(np.float32)
    pixels = np.nan_to_num(pixels, nan=0.0, posinf=0.0, neginf=0.0)

    n_components = min(settings.PCA_N_COMPONENTS, bands)
    pca = PCA(n_components=n_components)
    compressed = pca.fit_transform(pixels)
    explained_var = sum(pca.explained_variance_ratio_) * 100
    logger.info(f"  PCA: {bands} → {n_components} components ({explained_var:.1f}% variance)")

    spatial_image = compressed[:, 0].reshape(h, w)
    spatial_image = ((spatial_image - spatial_image.min()) /
                     (spatial_image.max() - spatial_image.min() + 1e-8) * 255).astype(np.uint8)

    # Downsample
    spatial_image, scale = _smart_downsample(spatial_image)
    metadata._preprocessing_scale = scale

    spatial_image = apply_clahe(spatial_image, clip_limit=3.0, tile_grid_size=8)
    save_preview(spatial_image, metadata.filepath)

    patches = extract_patches(spatial_image, patch_size=settings.PATCH_SIZE, overlap=settings.PATCH_OVERLAP)
    patches = _select_informative_patches(patches, MAX_PATCHES)

    return patches, spatial_image


def preprocess_image(
    pixel_data: np.ndarray,
    metadata: ImageMetadata,
) -> tuple[list[dict], np.ndarray]:
    """Main preprocessing entry point. Routes to instrument-specific pipeline."""
    instrument = metadata.instrument

    if instrument == InstrumentType.OHRC:
        return preprocess_ohrc(pixel_data, metadata)
    elif instrument == InstrumentType.TMC:
        return preprocess_tmc(pixel_data, metadata)
    elif instrument == InstrumentType.IIRS:
        return preprocess_iirs(pixel_data, metadata)
    else:
        logger.warning(f"Unknown instrument '{instrument}', using generic preprocessing")
        image = ensure_grayscale(pixel_data)
        if image.dtype != np.uint8:
            image = normalize_to_8bit(image)
        image, scale = _smart_downsample(image)
        metadata._preprocessing_scale = scale
        image = apply_clahe(image)
        save_preview(image, metadata.filepath)
        patches = extract_patches(image, settings.PATCH_SIZE, settings.PATCH_OVERLAP)
        patches = _select_informative_patches(patches, MAX_PATCHES)
        return patches, image
