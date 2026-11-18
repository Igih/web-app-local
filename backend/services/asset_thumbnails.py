from __future__ import annotations

import os
import uuid
from pathlib import Path

from PIL import Image

from config import ASSET_ORIGINALS_DIR, ASSET_THUMBNAILS_DIR


THUMBNAIL_SIZE = (320, 320)


def generate_thumbnail(storage_key: str) -> str | None:
    source = ASSET_ORIGINALS_DIR / storage_key
    if not source.exists():
        return None

    relative_target = Path(storage_key).with_suffix(".jpg")
    target = ASSET_THUMBNAILS_DIR / relative_target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.part")

    try:
        with Image.open(source) as image:
            image.thumbnail(THUMBNAIL_SIZE)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(temporary, format="JPEG", quality=85)
        os.replace(temporary, target)
        return relative_target.as_posix()
    except Exception:
        if temporary.exists():
            temporary.unlink()
        return None
