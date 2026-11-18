from __future__ import annotations

import logging
import os
import shutil
import uuid
from collections import defaultdict
from pathlib import Path

from psycopg2.extras import RealDictCursor

from config import ASSET_ANNOTATIONS_DIR
from services.asset_paths import is_image_file
from services.asset_storage import sha256_file, storage_key_for_sha256


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asset_annotations")


def _store_annotation_file(source_path: Path) -> dict:
    ASSET_ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    sha256 = sha256_file(source_path)
    storage_key = storage_key_for_sha256(sha256)
    final_path = ASSET_ANNOTATIONS_DIR / storage_key

    if not final_path.exists():
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = final_path.with_name(
            f".{final_path.name}.{uuid.uuid4().hex}.part"
        )
        try:
            shutil.copyfile(source_path, temporary_path)
            os.replace(temporary_path, final_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    return {"sha256": sha256, "storage_key": storage_key}


def _annotation_files(root: Path):
    if root.is_file():
        if not is_image_file(root):
            yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and not is_image_file(path):
            yield path


def _relative_annotation_path(root: Path, path: Path) -> str:
    if root.is_file():
        return path.name
    return path.resolve().relative_to(root.resolve()).as_posix()


def process_annotations_for_batch(conn, batch: dict) -> dict:
    if not batch.get("annotation_path"):
        return {"stored": 0, "matched": 0, "ambiguous": 0, "unmatched": 0}

    root = Path(batch["annotation_path"])
    if not root.exists():
        logger.warning("Annotation path does not exist: %s", root)
        return {"stored": 0, "matched": 0, "ambiguous": 0, "unmatched": 0}

    stored = 0
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for source_path in _annotation_files(root):
            relative_path = _relative_annotation_path(root, source_path)
            stored_file = _store_annotation_file(source_path)
            cur.execute(
                """
                INSERT INTO asset.annotation_files (
                    batch_id, storage_key, source_path, source_filename,
                    relative_path, sha256, match_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                ON CONFLICT (batch_id, relative_path) DO NOTHING
                """,
                (
                    batch["id"],
                    stored_file["storage_key"],
                    str(source_path),
                    source_path.name,
                    relative_path,
                    stored_file["sha256"],
                ),
            )
            if cur.rowcount:
                stored += 1

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE asset.annotation_files
            SET image_id = NULL, match_status = 'pending'
            WHERE batch_id = %s
            """,
            (batch["id"],),
        )

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, source_filename
            FROM asset.annotation_files
            WHERE batch_id = %s
            """,
            (batch["id"],),
        )
        annotation_rows = cur.fetchall()

        cur.execute(
            """
            SELECT image_id, source_filename
            FROM asset.import_items
            WHERE batch_id = %s AND image_id IS NOT NULL
            """,
            (batch["id"],),
        )
        item_rows = cur.fetchall()

    candidates: dict[str, set[int]] = defaultdict(set)
    for row in item_rows:
        stem = Path(row["source_filename"]).stem.lower()
        candidates[stem].add(row["image_id"])

    matched = 0
    ambiguous = 0
    unmatched = 0

    with conn.cursor() as cur:
        for row in annotation_rows:
            annotation_id = row["id"]
            stem = Path(row["source_filename"]).stem.lower()
            image_ids = candidates.get(stem, set())
            if len(image_ids) == 1:
                image_id = next(iter(image_ids))
                cur.execute(
                    """
                    UPDATE asset.annotation_files
                    SET image_id = %s, match_status = 'matched'
                    WHERE id = %s
                    """,
                    (image_id, annotation_id),
                )
                matched += 1
            elif len(image_ids) > 1:
                cur.execute(
                    """
                    UPDATE asset.annotation_files
                    SET match_status = 'ambiguous'
                    WHERE id = %s
                    """,
                    (annotation_id,),
                )
                ambiguous += 1
            else:
                cur.execute(
                    """
                    UPDATE asset.annotation_files
                    SET match_status = 'unmatched'
                    WHERE id = %s
                    """,
                    (annotation_id,),
                )
                unmatched += 1

    logger.info(
        "Annotations for batch %s: stored=%s matched=%s ambiguous=%s unmatched=%s",
        batch["id"],
        stored,
        matched,
        ambiguous,
        unmatched,
    )
    return {
        "stored": stored,
        "matched": matched,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
    }
