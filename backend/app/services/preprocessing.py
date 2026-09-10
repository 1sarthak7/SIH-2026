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
MAX_PROCESSING_DIM = 8192
MIN_PROCESSING_DIM = 1024  # Minimum dimension to preserve detail
MAX_PATCHES = 40
MAX_STRIP_SECTIONS = 5  # For very tall strip images, sample this many sections


def _smart_downsample(image: np.ndarray, max_dim: int = MAX_PROCESSING_DIM) -> tuple[np.ndarray, float]:
    """
    Downsample image intelligently for strip (pushbroom) images.
    
    OHRC/TMC images are strips: ~12000px wide but 100,000+ px tall.
    Simple max-dim downsampling destroys the width. Instead:
    - Ensure the SHORT dimension stays >= MIN_PROCESSING_DIM
    - For very tall strips, sample evenly-spaced sections
    """
    h, w = image.shape[:2]
    max_side = max(h, w)
    min_side = min(h, w)

    if max_side <= max_dim:
        return image, 1.0

    # Calculate scale based on max dimension
    scale = max_dim / max_side
    
    # But ensure min dimension stays at least MIN_PROCESSING_DIM
    if min_side * scale < MIN_PROCESSING_DIM:
        scale = MIN_PROCESSING_DIM / min_side
        logger.info(f"  Adjusted scale to preserve min dimension >= {MIN_PROCESSING_DIM}px")

    new_h = int(h * scale)
    new_w = int(w * scale)

    logger.info(f"  Downsampling: {w}×{h} → {new_w}×{new_h} (scale={scale:.4f})")
    downsampled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return downsampled, scale


def _sample_strip_sections(image: np.ndarray, num_sections: int = MAX_STRIP_SECTIONS, 
                           section_height: int = 2048) -> list[tuple[np.ndarray, int]]:
    """
    For very tall strip images, sample evenly-spaced horizontal sections.
    
    Returns list of (section_image, y_offset) tuples.
    """
    h, w = image.shape[:2]
    
    if h <= section_height * 2:
        return [(image, 0)]
    
    # Evenly space sections along the strip
    spacing = (h - section_height) // (num_sections - 1) if num_sections > 1 else 0
    sections = []
    
    for i in range(num_sections):
        y_start = min(i * spacing, h - section_height)
        section = image[y_start:y_start + section_height, :]
        sections.append((section, y_start))
        
    logger.info(f"  Sampled {len(sections)} sections of {section_height}px from {h}px strip")
    return sections


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
    OHRC Preprocessing Pipeline (optimized for pushbroom strips):
    1. Ensure grayscale + 8-bit
    2. Sample sections from the strip (don't downsample entire image)
    3. Downsample each section to ~1024px wide
    4. CLAHE
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

    h, w = image.shape[:2]
    
    # For strip images: sample sections, then downsample each section
    all_patches = []
    
    if h > 4096:
        # Strip image — sample sections along the height
        sections = _sample_strip_sections(image, num_sections=MAX_STRIP_SECTIONS, section_height=2048)
        
        for section_img, y_offset in sections:
            # Downsample section width to manageable size
            sec_downsampled, scale = _smart_downsample(section_img)
            sec_enhanced = apply_clahe(sec_downsampled, 
                                       clip_limit=settings.CLAHE_CLIP_LIMIT,
                                       tile_grid_size=settings.CLAHE_TILE_GRID)
            
            patches = extract_patches(sec_enhanced, patch_size=settings.PATCH_SIZE, 
                                      overlap=settings.PATCH_OVERLAP)
            
            # Adjust offsets to account for section position and scale
            for p in patches:
                p["offset_y"] = int(p["offset_y"] / scale) + y_offset
                p["offset_x"] = int(p["offset_x"] / scale)
                p["_scale"] = scale
            
            all_patches.extend(patches)
        
        metadata._preprocessing_scale = sections[0][0].shape[1] / w if sections else 1.0
    else:
        # Normal image — just downsample
        image, scale = _smart_downsample(image)
        metadata._preprocessing_scale = scale
        image = apply_clahe(image, clip_limit=settings.CLAHE_CLIP_LIMIT,
                           tile_grid_size=settings.CLAHE_TILE_GRID)
        all_patches = extract_patches(image, patch_size=settings.PATCH_SIZE,
                                      overlap=settings.PATCH_OVERLAP)

    logger.info(f"  Total patches before selection: {len(all_patches)}")

    # Save a preview (use middle section or downsampled image)
    preview_img, _ = _smart_downsample(pixel_data if pixel_data.ndim == 2 else ensure_grayscale(pixel_data),
                                        max_dim=2048)
    preview_img = apply_clahe(preview_img if preview_img.dtype == np.uint8 else normalize_to_8bit(preview_img))
    save_preview(preview_img, metadata.filepath)

    # Smart selection
    all_patches = _select_informative_patches(all_patches, MAX_PATCHES)

    return all_patches, preview_img


def preprocess_tmc(pixel_data: np.ndarray, metadata: ImageMetadata) -> tuple[list[dict], np.ndarray]:
    """
    TMC-2 Preprocessing Pipeline (strip-aware):
    1. Handle multi-band / 16-bit data
    2. Strip sampling for tall images
    3. CLAHE + smart patch extraction
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

    h, w = image.shape[:2]
    all_patches = []

    if h > 4096:
        # Strip image — sample sections
        sections = _sample_strip_sections(image, num_sections=MAX_STRIP_SECTIONS, section_height=2048)
        for section_img, y_offset in sections:
            sec_downsampled, scale = _smart_downsample(section_img)
            sec_enhanced = apply_clahe(sec_downsampled, clip_limit=2.5, tile_grid_size=8)
            patches = extract_patches(sec_enhanced, patch_size=settings.PATCH_SIZE, overlap=settings.PATCH_OVERLAP)
            for p in patches:
                p["offset_y"] = int(p["offset_y"] / scale) + y_offset
                p["offset_x"] = int(p["offset_x"] / scale)
                p["_scale"] = scale
            all_patches.extend(patches)
        metadata._preprocessing_scale = sections[0][0].shape[1] / w if sections else 1.0
    else:
        image, scale = _smart_downsample(image)
        metadata._preprocessing_scale = scale
        image = apply_clahe(image, clip_limit=2.5, tile_grid_size=8)
        all_patches = extract_patches(image, patch_size=settings.PATCH_SIZE, overlap=settings.PATCH_OVERLAP)

    logger.info(f"  Total patches before selection: {len(all_patches)}")

    # Preview
    preview_img, _ = _smart_downsample(pixel_data if pixel_data.ndim == 2 else ensure_grayscale(pixel_data), max_dim=2048)
    preview_img = apply_clahe(preview_img if preview_img.dtype == np.uint8 else normalize_to_8bit(preview_img))
    save_preview(preview_img, metadata.filepath)

    all_patches = _select_informative_patches(all_patches, MAX_PATCHES)

    return all_patches, preview_img


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
