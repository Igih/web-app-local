from enum import Enum


class CaptureType(str, Enum):
    PHOTO = "photo"
    HAND_DRAWN = "hand_drawn"


class SpectralType(str, Enum):
    VISIBLE = "visible"
    INFRARED = "infrared"


CAPTURE_TYPES = {item.value for item in CaptureType}
SPECTRAL_TYPES = {item.value for item in SpectralType}


def is_valid_type_pair(capture_type: str | None, spectral_type: str | None) -> bool:
    """Return whether the two-level type combination is consistent."""
    if spectral_type is not None and capture_type is None:
        return False
    if capture_type is not None and capture_type not in CAPTURE_TYPES:
        return False
    if spectral_type is not None and spectral_type not in SPECTRAL_TYPES:
        return False
    return True
