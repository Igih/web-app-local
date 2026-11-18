import pytest

from models.asset_image import AssetImageUpdate
from services.asset_images import _validate_payload


def test_valid_payload() -> None:
    _validate_payload(AssetImageUpdate(capture_type="photo", spectral_type="visible"))


def test_invalid_capture_type() -> None:
    with pytest.raises(Exception) as exc:
        _validate_payload(AssetImageUpdate(capture_type="wrong"))
    assert exc.value.status_code == 400


def test_too_many_tags() -> None:
    with pytest.raises(Exception) as exc:
        _validate_payload(AssetImageUpdate(tags=["1", "2", "3", "4", "5", "6"]))
    assert exc.value.status_code == 400
