"""
Data Ingestion Service — Step 1

Parses Chandrayaan-2 image files (PDS4, GeoTIFF, standard images)
and extracts pixel data + spatial metadata.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from loguru import logger

from app.models.schemas import ImageMetadata, InstrumentType


def detect_instrument(filepath: str, metadata: dict) -> InstrumentType:
    """
    Detect the Chandrayaan-2 instrument from filename patterns or metadata tags.

    Heuristics:
    - Filenames containing 'ohrc' → OHRC
    - Filenames containing 'tmc' → TMC
    - Filenames containing 'iirs' → IIRS
    - Files with many bands (>10) → likely IIRS
    - Very high resolution (<1m) → likely OHRC
    """
    fname = Path(filepath).stem.lower()

    # Check filename patterns
    if "ohrc" in fname:
        return InstrumentType.OHRC
    if "tmc" in fname:
        return InstrumentType.TMC
    if "iirs" in fname:
        return InstrumentType.IIRS

    # Check band count (IIRS has 256 bands)
    num_bands = metadata.get("num_bands", 1)
    if num_bands > 10:
        return InstrumentType.IIRS

    # Check resolution (OHRC ≈ 0.25m, TMC ≈ 5m)
    resolution = metadata.get("resolution_m", 0)
    if resolution > 0:
        if resolution < 1.0:
            return InstrumentType.OHRC
        elif resolution < 10.0:
            return InstrumentType.TMC

    logger.warning(f"Could not determine instrument for {filepath}, defaulting to UNKNOWN")
    return InstrumentType.UNKNOWN


def _extract_resolution(transform) -> float:
    """Extract ground resolution in meters/pixel from the affine transform."""
    if transform is None:
        return 0.0
    # The pixel size is in the transform's scale components
    # For projected CRS: already in meters
    # For geographic CRS: need to convert degrees to meters (1° ≈ 1737.4km on Moon / 360 * pi)
    pixel_size_x = abs(transform.a)
    pixel_size_y = abs(transform.e)
    resolution = (pixel_size_x + pixel_size_y) / 2.0

    # If resolution is very small (likely in degrees), convert to meters
    # Moon's mean radius = 1737.4 km
    if resolution < 0.01:  # Likely degrees
        resolution = resolution * (np.pi / 180.0) * 1737400.0  # meters

    return resolution


def ingest_geotiff(filepath: str) -> tuple[np.ndarray, ImageMetadata]:
    """
    Parse a GeoTIFF file using Rasterio.

    Returns:
        - pixel_data: numpy array of shape (bands, height, width) or (height, width)
        - metadata: ImageMetadata with spatial info
    """
    logger.info(f"Ingesting GeoTIFF: {filepath}")

    with rasterio.open(filepath) as src:
        # Read all bands
        pixel_data = src.read()  # shape: (bands, H, W)

        # Extract spatial bounds
        bounds = src.bounds  # BoundingBox(left, bottom, right, top)
        transform = src.transform
        crs = str(src.crs) if src.crs else "UNKNOWN"

        resolution = _extract_resolution(transform)

        meta_dict = {
            "num_bands": src.count,
            "resolution_m": resolution,
        }

        instrument = detect_instrument(filepath, meta_dict)

        metadata = ImageMetadata(
            instrument=instrument,
            filepath=filepath,
            width=src.width,
            height=src.height,
            num_bands=src.count,
            resolution_m=resolution,
            crs=crs,
            bbox_lon_min=bounds.left,
            bbox_lat_min=bounds.bottom,
            bbox_lon_max=bounds.right,
            bbox_lat_max=bounds.top,
        )

    # If single band, squeeze to 2D
    if pixel_data.shape[0] == 1:
        pixel_data = pixel_data[0]  # (H, W)

    logger.info(
        f"  Ingested: {metadata.instrument.value} | "
        f"{metadata.width}×{metadata.height} | "
        f"{metadata.num_bands} bands | "
        f"{metadata.resolution_m:.2f} m/px"
    )

    return pixel_data, metadata


def ingest_standard_image(filepath: str) -> tuple[np.ndarray, ImageMetadata]:
    """
    Parse standard image formats (PNG, JPG) that lack geospatial metadata.
    Used for testing/demo with non-PDS4 files.

    Creates synthetic metadata with pixel-based coordinates.
    """
    from PIL import Image

    logger.info(f"Ingesting standard image: {filepath}")

    img = Image.open(filepath)
    pixel_data = np.array(img)

    # Convert to grayscale if RGB
    if pixel_data.ndim == 3:
        if pixel_data.shape[2] == 4:  # RGBA
            pixel_data = pixel_data[:, :, :3]
        if pixel_data.shape[2] == 3:
            # Keep as multi-band for potential IIRS-like handling
            pass

    num_bands = pixel_data.shape[2] if pixel_data.ndim == 3 else 1
    height = pixel_data.shape[0]
    width = pixel_data.shape[1]

    meta_dict = {"num_bands": num_bands, "resolution_m": 1.0}
    instrument = detect_instrument(filepath, meta_dict)

    metadata = ImageMetadata(
        instrument=instrument,
        filepath=filepath,
        width=width,
        height=height,
        num_bands=num_bands,
        resolution_m=1.0,  # Default: 1 meter/pixel
        crs="PIXEL",  # No real CRS
        bbox_lon_min=0.0,
        bbox_lat_min=0.0,
        bbox_lon_max=float(width),
        bbox_lat_max=float(height),
    )

    # If multi-band, rearrange to (bands, H, W) for consistency
    if pixel_data.ndim == 3:
        pixel_data = np.transpose(pixel_data, (2, 0, 1))  # (H,W,C) → (C,H,W)

    logger.info(
        f"  Ingested: {metadata.instrument.value} | "
        f"{width}×{height} | {num_bands} bands"
    )

    return pixel_data, metadata


def ingest_image(filepath: str) -> tuple[np.ndarray, ImageMetadata]:
    """
    Main ingestion entry point. Routes to the appropriate parser based on file extension.

    Returns:
        - pixel_data: numpy array
        - metadata: ImageMetadata
    """
    ext = Path(filepath).suffix.lower()

    if ext in {".tif", ".tiff", ".geotiff"}:
        return ingest_geotiff(filepath)
    elif ext in {".img"}:
        # PDS4 .img files can often be read by GDAL/Rasterio
        try:
            return ingest_geotiff(filepath)
        except Exception as e:
            logger.warning(f"Failed to read {filepath} as GeoTIFF, trying raw: {e}")
            return _ingest_raw_pds4(filepath)
    elif ext in {".png", ".jpg", ".jpeg"}:
        return ingest_standard_image(filepath)
    else:
        # Try rasterio first, fall back to standard image
        try:
            return ingest_geotiff(filepath)
        except Exception:
            return ingest_standard_image(filepath)


def _ingest_raw_pds4(filepath: str) -> tuple[np.ndarray, ImageMetadata]:
    """
    Fallback parser for PDS4 .img files that Rasterio can't read.
    Attempts to read the XML label file for metadata and the .img as raw binary.
    """
    import xml.etree.ElementTree as ET

    img_path = Path(filepath)
    label_path = img_path.with_suffix(".xml")

    # Default dimensions (will be overridden if label exists)
    width, height, bands = 1024, 1024, 1
    dtype = np.uint16  # OHRC is typically 10-bit stored as 16-bit

    if label_path.exists():
        try:
            tree = ET.parse(str(label_path))
            root = tree.getroot()
            # PDS4 namespace handling
            ns = {"pds": "http://pds.nasa.gov/pds4/pds/v1"}

            # Try to find array dimensions
            for elem in root.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag == "lines":
                    height = int(elem.text)
                elif tag == "samples":
                    width = int(elem.text)
                elif tag == "bands":
                    bands = int(elem.text)

            logger.info(f"  PDS4 label: {width}×{height}, {bands} bands")
        except Exception as e:
            logger.warning(f"  Could not parse PDS4 label: {e}")

    # Read raw binary
    raw = np.fromfile(str(img_path), dtype=dtype)

    try:
        if bands > 1:
            pixel_data = raw.reshape(bands, height, width)
        else:
            pixel_data = raw.reshape(height, width)
    except ValueError:
        # If reshape fails, try to infer dimensions
        total = len(raw)
        side = int(np.sqrt(total))
        pixel_data = raw[:side * side].reshape(side, side)
        height, width = side, side
        logger.warning(f"  Reshaped to {side}×{side} (inferred)")

    meta_dict = {"num_bands": bands, "resolution_m": 0.25}
    instrument = detect_instrument(filepath, meta_dict)

    metadata = ImageMetadata(
        instrument=instrument,
        filepath=filepath,
        width=width,
        height=height,
        num_bands=bands,
        resolution_m=0.25,  # OHRC default
        crs="UNKNOWN",
        bbox_lon_min=0.0,
        bbox_lat_min=0.0,
        bbox_lon_max=float(width) * 0.25,
        bbox_lat_max=float(height) * 0.25,
    )

    return pixel_data, metadata
