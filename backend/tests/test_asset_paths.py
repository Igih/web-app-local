from pathlib import Path

import pytest

from services.asset_paths import validate_asset_path


def test_allowed_path_inside_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    image = allowed / "flower.jpg"
    image.write_bytes(b"fake")

    resolved = validate_asset_path(str(image), [str(allowed)])
    assert resolved == image.resolve()


def test_path_outside_root_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"fake")

    with pytest.raises(Exception) as exc:
        validate_asset_path(str(outside), [str(allowed)])
    assert exc.value.status_code == 403


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "secret.jpg"
    outside.write_bytes(b"fake")

    symlink = allowed / "link.jpg"
    symlink.symlink_to(outside)

    with pytest.raises(Exception) as exc:
        validate_asset_path(str(symlink), [str(allowed)])
    assert exc.value.status_code == 403
