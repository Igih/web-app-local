from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path

from config import ASSET_ORIGINALS_DIR


_CHUNK_SIZE = 1024 * 1024


def ensure_originals_directory() -> None:
    ASSET_ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_obj:
        while True:
            chunk = file_obj.read(_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def storage_key_for_sha256(sha256: str) -> str:
    return f"{sha256[:2]}/{sha256[2:4]}/{sha256}"


def store_original(source_path: str | Path) -> dict:
    source = Path(source_path)
    ensure_originals_directory()

    sha256 = sha256_file(source)
    storage_key = storage_key_for_sha256(sha256)
    final_path = ASSET_ORIGINALS_DIR / storage_key

    if final_path.exists() and final_path.stat().st_size > 0:
        return {
            "sha256": sha256,
            "storage_key": storage_key,
            "byte_size": final_path.stat().st_size,
            "existed": True,
        }

    final_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = final_path.with_name(
        f".{final_path.name}.{uuid.uuid4().hex}.part"
    )
    try:
        shutil.copyfile(source, temporary_path)
        os.replace(temporary_path, final_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        "sha256": sha256,
        "storage_key": storage_key,
        "byte_size": final_path.stat().st_size,
        "existed": False,
    }
