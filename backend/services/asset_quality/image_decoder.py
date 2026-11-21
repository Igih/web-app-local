from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from config import QUALITY_ANALYSIS_LONG_SIDE


RGB_TO_GRAY_WEIGHTS = (0.299, 0.587, 0.114)


def _read_tiff(path: Path) -> np.ndarray:
    try:
        import tifffile
    except ImportError as exc:  # pragma: no cover - fallback path
        raise ValueError("tifffile is required for TIFF quality analysis") from exc

    image = tifffile.imread(str(path))
    if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
        raise ValueError("multi-page TIFF is not supported by quality precheck")
    if image.ndim == 3 and image.shape[2] == 1:
        image = image[:, :, 0]
    return image


def _read_with_pil(path: Path) -> np.ndarray:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        return np.asarray(image)


def load_source_array(path: Path) -> np.ndarray:
    """Return an image array without mutating the source file."""
    suffix = path.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        return _read_tiff(path)
    return _read_with_pil(path)


def _bit_depth_from_dtype(dtype: np.dtype) -> int:
    if dtype == np.uint8:
        return 8
    if dtype == np.uint16:
        return 16
    if dtype in (np.int8,):
        return 8
    if dtype in (np.int16,):
        return 16
    if dtype == np.uint32:
        return 32
    if np.issubdtype(dtype, np.floating):
        return 32
    return int(np.iinfo(dtype).bits) if np.issubdtype(dtype, np.integer) else 0


def _color_mode(path: Path, array: np.ndarray) -> str:
    suffix = path.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        if array.ndim == 2:
            return "L"
        if array.shape[2] == 3:
            return "RGB"
        if array.shape[2] == 4:
            return "RGBA"
    try:
        with Image.open(path) as image:
            return image.mode
    except Exception:
        return "unknown"


def _resize_long_side(image: np.ndarray, long_side: int) -> tuple[np.ndarray, float]:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= long_side:
        return image, 1.0

    scale = long_side / longest
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(image, (new_width, new_height), interpolation=interpolation), scale


def to_gray_uint8(image: np.ndarray) -> np.ndarray:
    """Convert an array to a fixed gray uint8 analysis copy.

    RGB conversion uses the fixed Rec.601-style weights. 16-bit values are
    linearly mapped to uint8 only for edge/texture analysis; raw range metrics
    are still calculated from the original array by the metric module.
    """
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]

    if image.ndim == 3 and image.shape[2] == 3:
        gray = np.dot(image.astype(np.float64), RGB_TO_GRAY_WEIGHTS)
    elif image.ndim == 2:
        gray = image.astype(np.float64)
    else:
        gray = image[:, :, 0].astype(np.float64)

    if gray.size == 0:
        raise ValueError("empty image")

    if image.dtype == np.uint16:
        low = float(gray.min())
        high = float(gray.max())
        if high <= low:
            return np.zeros(gray.shape, dtype=np.uint8)
        gray = (gray - low) / (high - low)
    elif image.dtype == np.uint8:
        gray = gray / 255.0
    else:
        gray = np.clip(gray, 0.0, 1.0)

    return (gray * 255.0).astype(np.uint8)


def decode_for_analysis(path: Path) -> dict:
    """Decode a source image for quality analysis without changing it."""
    source = load_source_array(path)
    original_height, original_width = source.shape[:2]
    bit_depth = _bit_depth_from_dtype(source.dtype)
    channels = 1 if source.ndim == 2 else source.shape[2]
    color_mode = _color_mode(path, source)

    analysis_image, scale = _resize_long_side(
        source, QUALITY_ANALYSIS_LONG_SIDE
    )
    gray_u8 = to_gray_uint8(analysis_image)

    return {
        "array": source,
        "analysis_image": analysis_image,
        "gray_u8": gray_u8,
        "original_width": original_width,
        "original_height": original_height,
        "analysis_width": gray_u8.shape[1],
        "analysis_height": gray_u8.shape[0],
        "analysis_scale": scale,
        "bit_depth": bit_depth,
        "channels": channels,
        "color_mode": color_mode,
    }


def profile_key_for_candidate(
    capture_type: str | None,
    spectral_type: str | None,
    bit_depth: int | None,
) -> str:
    if capture_type is None or spectral_type is None:
        return "unspecified"

    bit_part = ""
    if bit_depth in (8, 16):
        bit_part = f"_{bit_depth}bit"
    return f"{capture_type}_{spectral_type}{bit_part}"
