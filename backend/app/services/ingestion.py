"""
Data Ingestion Service — Step 1 (Updated for real ISRO PDS4 data)

Parses Chandrayaan-2 image files from ISRO PRADAN:
- OHRC: UnsignedByte (8-bit), 12000×101063, Polar Stereographic
- TMC-2: UnsignedLSB2 (16-bit LE), 4000×148108, Selenographic
- IIRS: Multi-band hyperspectral

Each product directory contains:
  data/calibrated/<date>/<name>.img + .xml (image + PDS4 label)
  geometry/calibrated/<date>/<name>.csv (per-pixel lat/lon grid)
  browse/calibrated/<date>/<name>.png (thumbnail preview)
"""

from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from loguru import logger

from app.models.schemas import ImageMetadata, InstrumentType


# PDS4 data type mapping
PDS4_DTYPES = {
    "UnsignedByte": np.uint8,
    "UnsignedLSB2": np.dtype("<u2"),   # 16-bit unsigned, little-endian
    "SignedLSB2": np.dtype("<i2"),      # 16-bit signed, little-endian
    "UnsignedMSB2": np.dtype(">u2"),   # 16-bit unsigned, big-endian
    "IEEE754LSBSingle": np.dtype("<f4"), # 32-bit float, little-endian
}


def _parse_pds4_xml(xml_path: str) -> dict:
    """
    Parse a PDS4 XML label file from ISRO PRADAN.
    
    Extracts image dimensions, data type, instrument info, coordinates,
    and illumination parameters.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Handle PDS4 namespace
    nsmap = {
        "pds": "http://pds.nasa.gov/pds4/pds/v1",
        "isda": "https://isda.issdc.gov.in/pds4/isda/v1",
    }

    meta = {}

    # --- Instrument detection from title ---
    title_elem = root.find(".//pds:title", nsmap) 
    if title_elem is None:
        # Try without namespace
        title_elem = root.find(".//title")
    title = title_elem.text.lower() if title_elem is not None else ""

    if "ohrc" in title or "high resolution" in title:
        meta["instrument"] = InstrumentType.OHRC
    elif "tmc" in title or "terrain mapping" in title:
        meta["instrument"] = InstrumentType.TMC
    elif "iirs" in title:
        meta["instrument"] = InstrumentType.IIRS
    else:
        meta["instrument"] = InstrumentType.UNKNOWN

    # --- Image dimensions and data type from Array_2D_Image ---
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "data_type":
            meta["data_type"] = elem.text.strip()

    # Parse all Axis_Array elements for dimensions
    for axis in root.iter():
        axis_tag = axis.tag.split("}")[-1] if "}" in axis.tag else axis.tag
        if axis_tag == "Axis_Array":
            name_elem = None
            elems_elem = None
            for child in axis:
                child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child_tag == "axis_name":
                    name_elem = child
                elif child_tag == "elements":
                    elems_elem = child
            if name_elem is not None and elems_elem is not None:
                axis_name = name_elem.text.strip()
                axis_count = int(elems_elem.text.strip())
                if axis_name == "Line":
                    meta["lines"] = axis_count
                elif axis_name == "Sample":
                    meta["samples"] = axis_count
                elif axis_name == "Band":
                    meta["bands"] = axis_count

    # --- ISDA-specific parameters ---
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        text = elem.text.strip() if elem.text else ""

        if tag == "pixel_resolution":
            try:
                meta["resolution_m"] = float(text)
            except ValueError:
                pass
        elif tag == "sun_azimuth":
            try:
                meta["sun_azimuth"] = float(text)
            except ValueError:
                pass
        elif tag == "sun_elevation":
            try:
                meta["sun_elevation"] = float(text)
            except ValueError:
                pass
        elif tag == "spacecraft_altitude":
            try:
                meta["altitude_km"] = float(text)
            except ValueError:
                pass
        elif tag == "projection":
            meta["projection"] = text
        elif tag == "area":
            meta["area"] = text

    # --- Corner coordinates from Refined_Corner_Coordinates ---
    refined = None
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "Refined_Corner_Coordinates":
            refined = elem
            break

    if refined is None:
        # Fallback to System_Level_Coordinates
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "System_Level_Coordinates":
                refined = elem
                break

    if refined is not None:
        for child in refined:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            text = child.text.strip() if child.text else ""
            try:
                if "upper_left_lat" in tag:
                    meta["ul_lat"] = float(text)
                elif "upper_left_lon" in tag:
                    meta["ul_lon"] = float(text)
                elif "upper_right_lat" in tag:
                    meta["ur_lat"] = float(text)
                elif "upper_right_lon" in tag:
                    meta["ur_lon"] = float(text)
                elif "lower_left_lat" in tag:
                    meta["ll_lat"] = float(text)
                elif "lower_left_lon" in tag:
                    meta["ll_lon"] = float(text)
                elif "lower_right_lat" in tag:
                    meta["lr_lat"] = float(text)
                elif "lower_right_lon" in tag:
                    meta["lr_lon"] = float(text)
            except ValueError:
                pass

    # --- Acquisition date ---
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "start_date_time" and elem.text:
            meta["acquisition_date"] = elem.text.strip()
            break

    return meta


def _find_product_files(path: str) -> dict:
    """
    Given a path (could be a directory or a file), find all related product files.
    
    ISRO PRADAN structure:
      <product_dir>/
        data/calibrated/<date>/<name>.img + .xml
        geometry/calibrated/<date>/<name>.csv
        browse/calibrated/<date>/<name>.png
    """
    path = Path(path)
    files = {}

    if path.is_file():
        # Given a specific file — find siblings
        files["image"] = str(path) if path.suffix == ".img" else None
        files["label"] = str(path.with_suffix(".xml")) if path.with_suffix(".xml").exists() else None

        # Try to find geometry CSV
        product_dir = path
        for _ in range(5):  # Walk up to find the product root
            product_dir = product_dir.parent
            geom_dir = product_dir / "geometry"
            if geom_dir.exists():
                break

        csv_files = list(product_dir.rglob("*_g_grd_*.csv"))
        files["geometry_csv"] = str(csv_files[0]) if csv_files else None

        png_files = list(product_dir.rglob("*_b_brw_*.png"))
        files["browse_png"] = str(png_files[0]) if png_files else None

    elif path.is_dir():
        # Given a product directory — search for files
        img_files = list(path.rglob("*_d_img_*.img"))
        files["image"] = str(img_files[0]) if img_files else None

        xml_files = list(path.rglob("*_d_img_*.xml"))
        files["label"] = str(xml_files[0]) if xml_files else None

        csv_files = list(path.rglob("*_g_grd_*.csv"))
        files["geometry_csv"] = str(csv_files[0]) if csv_files else None

        png_files = list(path.rglob("*_b_brw_*.png"))
        files["browse_png"] = str(png_files[0]) if png_files else None

    return files


def ingest_pds4_product(filepath: str) -> tuple[np.ndarray, ImageMetadata, Optional[pd.DataFrame]]:
    """
    Ingest a real ISRO PRADAN PDS4 product.

    Args:
        filepath: Path to .img file, .xml label, or product directory

    Returns:
        - pixel_data: 2D numpy array (height, width)
        - metadata: ImageMetadata with all spatial info
        - geometry_df: DataFrame with per-pixel Lon/Lat/Pixel/Scan (or None)
    """
    logger.info(f"Ingesting PDS4 product: {filepath}")

    # Find all related files
    files = _find_product_files(filepath)

    if not files.get("image"):
        raise FileNotFoundError(f"No .img file found for {filepath}")
    if not files.get("label"):
        raise FileNotFoundError(f"No .xml label found for {filepath}")

    logger.info(f"  Image: {files['image']}")
    logger.info(f"  Label: {files['label']}")
    logger.info(f"  Geometry: {files.get('geometry_csv', 'Not found')}")

    # Parse XML label
    meta = _parse_pds4_xml(files["label"])

    lines = meta.get("lines", 0)
    samples = meta.get("samples", 0)
    bands = meta.get("bands", 1)
    data_type_str = meta.get("data_type", "UnsignedByte")
    dtype = PDS4_DTYPES.get(data_type_str, np.uint8)

    logger.info(f"  Dimensions: {samples}×{lines} ({data_type_str})")
    logger.info(f"  Instrument: {meta.get('instrument', 'unknown')}")

    # Read raw binary image
    raw = np.fromfile(files["image"], dtype=dtype)

    expected_size = lines * samples * bands
    if raw.size != expected_size:
        logger.warning(f"  Size mismatch: got {raw.size}, expected {expected_size}")
        # Try to reshape with actual size
        if raw.size > samples:
            lines = raw.size // (samples * bands)
            logger.info(f"  Adjusted lines to {lines}")

    if bands > 1:
        pixel_data = raw[:lines * samples * bands].reshape(bands, lines, samples)
    else:
        pixel_data = raw[:lines * samples].reshape(lines, samples)

    # Compute bounding box from corner coordinates
    lats = [meta.get(k, 0) for k in ["ul_lat", "ur_lat", "ll_lat", "lr_lat"]]
    lons = [meta.get(k, 0) for k in ["ul_lon", "ur_lon", "ll_lon", "lr_lon"]]

    # Read geometry CSV if available
    geometry_df = None
    if files.get("geometry_csv"):
        try:
            geometry_df = pd.read_csv(files["geometry_csv"])
            logger.info(f"  Geometry grid: {len(geometry_df)} points")
        except Exception as e:
            logger.warning(f"  Could not read geometry CSV: {e}")

    # Build metadata
    metadata = ImageMetadata(
        instrument=meta.get("instrument", InstrumentType.UNKNOWN),
        filepath=files["image"],
        width=samples,
        height=lines,
        num_bands=bands,
        resolution_m=meta.get("resolution_m", 1.0),
        crs=meta.get("projection", "Selenographic"),
        bbox_lat_min=min(lats) if any(lats) else 0.0,
        bbox_lat_max=max(lats) if any(lats) else 0.0,
        bbox_lon_min=min(lons) if any(lons) else 0.0,
        bbox_lon_max=max(lons) if any(lons) else 0.0,
        sun_elevation=meta.get("sun_elevation"),
        sun_azimuth=meta.get("sun_azimuth"),
        acquisition_date=meta.get("acquisition_date"),
    )

    logger.info(
        f"  ✅ Loaded: {metadata.instrument.value.upper()} | "
        f"{metadata.width}×{metadata.height} | "
        f"{metadata.resolution_m} m/px | "
        f"Sun elev: {metadata.sun_elevation}°"
    )

    return pixel_data, metadata, geometry_df


def ingest_standard_image(filepath: str) -> tuple[np.ndarray, ImageMetadata, None]:
    """
    Fallback for standard image formats (PNG, JPG, TIFF).
    """
    from PIL import Image
    import cv2

    logger.info(f"Ingesting standard image: {filepath}")

    ext = Path(filepath).suffix.lower()
    
    if ext in {".tif", ".tiff"}:
        try:
            import rasterio
            with rasterio.open(filepath) as src:
                pixel_data = src.read()
                if pixel_data.shape[0] == 1:
                    pixel_data = pixel_data[0]
                bounds = src.bounds
                transform = src.transform
                resolution = (abs(transform.a) + abs(transform.e)) / 2.0
                if resolution < 0.01:
                    resolution = resolution * (np.pi / 180.0) * 1737400.0
                    
                metadata = ImageMetadata(
                    instrument=InstrumentType.UNKNOWN,
                    filepath=filepath,
                    width=src.width,
                    height=src.height,
                    num_bands=src.count,
                    resolution_m=resolution,
                    crs=str(src.crs) if src.crs else "UNKNOWN",
                    bbox_lon_min=bounds.left,
                    bbox_lat_min=bounds.bottom,
                    bbox_lon_max=bounds.right,
                    bbox_lat_max=bounds.top,
                )
                return pixel_data, metadata, None
        except Exception as e:
            logger.warning(f"Rasterio failed, trying PIL: {e}")

    img = Image.open(filepath)
    pixel_data = np.array(img)

    if pixel_data.ndim == 3 and pixel_data.shape[2] in (3, 4):
        pixel_data = cv2.cvtColor(pixel_data[:, :, :3], cv2.COLOR_RGB2GRAY)

    h, w = pixel_data.shape[:2]
    
    # Detect instrument from filename
    fname = Path(filepath).stem.lower()
    instrument = InstrumentType.UNKNOWN
    if "ohr" in fname: instrument = InstrumentType.OHRC
    elif "tmc" in fname: instrument = InstrumentType.TMC
    elif "iirs" in fname: instrument = InstrumentType.IIRS

    metadata = ImageMetadata(
        instrument=instrument,
        filepath=filepath,
        width=w,
        height=h,
        num_bands=1,
        resolution_m=1.0,
        crs="PIXEL",
        bbox_lon_min=0, bbox_lat_min=0,
        bbox_lon_max=float(w), bbox_lat_max=float(h),
    )
    return pixel_data, metadata, None


def ingest_image(filepath: str) -> tuple[np.ndarray, ImageMetadata, Optional[pd.DataFrame]]:
    """
    Main ingestion entry point. Detects format and routes to the right parser.

    Returns:
        - pixel_data: numpy array (2D or 3D)
        - metadata: ImageMetadata
        - geometry_df: Per-pixel coordinate grid (if available)
    """
    path = Path(filepath)

    # Check if it's an ISRO PRADAN product directory
    if path.is_dir():
        img_files = list(path.rglob("*_d_img_*.img"))
        if img_files:
            return ingest_pds4_product(filepath)

    # Check file extension
    ext = path.suffix.lower()

    if ext == ".img":
        # Look for companion XML label
        xml_path = path.with_suffix(".xml")
        if xml_path.exists():
            return ingest_pds4_product(filepath)
        else:
            # Try product directory approach
            return ingest_pds4_product(str(path.parent.parent.parent.parent))

    elif ext == ".xml":
        # XML label — find the .img
        img_path = path.with_suffix(".img")
        if img_path.exists():
            return ingest_pds4_product(str(img_path))

    elif ext in {".tif", ".tiff", ".png", ".jpg", ".jpeg"}:
        return ingest_standard_image(filepath)

    # Fallback
    return ingest_standard_image(filepath)
