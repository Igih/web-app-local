from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".gif",
    ".tif",
    ".tiff",
}


def _resolved_root(root: str | Path) -> Path:
    return Path(root).expanduser().resolve(strict=False)


def validate_asset_path(
    raw_path: str,
    allowed_roots: list[str],
    *,
    must_exist: bool = True,
) -> Path:
    if not raw_path or not raw_path.strip():
        raise HTTPException(status_code=400, detail="Path is required")

    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")

    try:
        resolved = candidate.resolve(strict=must_exist)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Path does not exist") from exc

    allowed = [_resolved_root(root) for root in allowed_roots]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise HTTPException(status_code=403, detail="Path is outside authorized directories")

    return resolved


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def iter_image_paths(root: Path, recursive: bool):
    if root.is_file():
        if is_image_file(root):
            yield root
        return

    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        try:
            if is_image_file(path):
                yield path
        except OSError:
            continue
