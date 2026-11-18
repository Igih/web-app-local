from pathlib import Path

from services.asset_import import _iter_image_paths


def test_iter_image_paths_finds_images(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"fake")
    (tmp_path / "b.png").write_bytes(b"fake")
    (tmp_path / "note.txt").write_text("ignore")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.tiff").write_bytes(b"fake")

    paths = list(_iter_image_paths(tmp_path, recursive=True))
    assert len(paths) == 3


def test_iter_image_paths_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"fake")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.jpg").write_bytes(b"fake")

    paths = list(_iter_image_paths(tmp_path, recursive=False))
    assert [path.name for path in paths] == ["a.jpg"]
