from __future__ import annotations

import math

import numpy as np
from skimage.measure import blur_effect
from skimage.restoration import estimate_sigma

from config import QUALITY_ALGORITHM_VERSION, QUALITY_PREPROCESS_VERSION


def _safe_float(value: float) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _blur_effect(gray_u8: np.ndarray) -> float | None:
    try:
        return float(blur_effect(gray_u8))
    except Exception:
        return None


def _noise_metrics(gray_u8: np.ndarray) -> tuple[float, float]:
    try:
        sigma = float(estimate_sigma(gray_u8, average_sigmas=True))
        return sigma, 1.0
    except Exception:
        return 0.0, 0.0


def calculate_metrics(decoded: dict, source_dtype) -> dict:
    """Calculate Q1 metrics from a decoded analysis copy."""
    source = decoded["array"]
    gray_u8 = decoded["gray_u8"]
    bit_depth = decoded["bit_depth"]

    if source.dtype == np.uint8:
        if source.ndim == 3 and source.shape[2] >= 3:
            gray = np.dot(source[:, :, :3].astype(np.float64), (0.299, 0.587, 0.114))
        elif source.ndim == 3:
            gray = source[:, :, 0].astype(np.float64)
        else:
            gray = source.astype(np.float64)
        normalized = gray / 255.0
        raw_min = float(gray.min())
        raw_max = float(gray.max())
        p01 = float(np.percentile(gray, 1))
        p99 = float(np.percentile(gray, 99))
    elif source.dtype == np.uint16:
        if source.ndim == 3 and source.shape[2] >= 3:
            gray = np.dot(source[:, :, :3].astype(np.float64), (0.299, 0.587, 0.114))
        elif source.ndim == 3:
            gray = source[:, :, 0].astype(np.float64)
        else:
            gray = source.astype(np.float64)
        normalized = gray / 65535.0
        raw_min = float(gray.min())
        raw_max = float(gray.max())
        p01 = float(np.percentile(gray, 1))
        p99 = float(np.percentile(gray, 99))
    else:
        if source.ndim == 3:
            gray = source[:, :, 0].astype(np.float64)
        else:
            gray = source.astype(np.float64)
        low, high = float(gray.min()), float(gray.max())
        normalized = (gray - low) / (high - low) if high > low else np.zeros_like(gray)
        raw_min = low
        raw_max = high
        p01 = float(np.percentile(gray, 1))
        p99 = float(np.percentile(gray, 99))

    rms_contrast = float(np.std(normalized))
    bright_threshold = 0.95
    bright_fraction = float((normalized > bright_threshold).mean())
    noise_sigma, noise_confidence = _noise_metrics(gray_u8)

    comparable = bit_depth in (8,)
    metrics = {
        "blur_effect": _safe_float(_blur_effect(gray_u8)),
        "rms_contrast": _safe_float(rms_contrast),
        "bright_fraction": _safe_float(bright_fraction),
        "noise_sigma": _safe_float(noise_sigma),
        "noise_confidence": _safe_float(noise_confidence),
        "raw_min": _safe_float(raw_min),
        "raw_max": _safe_float(raw_max),
        "p01": _safe_float(p01),
        "p99": _safe_float(p99),
        "comparable": comparable,
        "preprocess_version": QUALITY_PREPROCESS_VERSION,
        "algorithm_version": QUALITY_ALGORITHM_VERSION,
    }
    return metrics
