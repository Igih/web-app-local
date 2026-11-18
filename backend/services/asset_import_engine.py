from __future__ import annotations

import logging
import socket
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from PIL import Image

from config import DB_CONFIG
from services.asset_storage import store_original
from services.asset_thumbnails import generate_thumbnail
from services.asset_paths import iter_image_paths
from services.asset_annotations import process_annotations_for_batch


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asset_import_engine")

_SOURCE_MACHINE = socket.gethostname()


def _connect():
    return psycopg2.connect(**DB_CONFIG)


def _normalized_relative_path(root: Path, path: Path) -> str:
    if root.is_file():
        return path.name
    return path.resolve().relative_to(root.resolve()).as_posix()


def _ensure_import_items(conn, batch: dict) -> None:
    root = Path(batch["image_path"])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for image_path in iter_image_paths(root, batch["recursive"]):
            normalized = _normalized_relative_path(root, image_path)
            cur.execute(
                """
                INSERT INTO asset.import_items (
                    batch_id, source_path, normalized_relative_path,
                    source_filename, source_machine, status
                )
                VALUES (%s, %s, %s, %s, %s, 'pending')
                ON CONFLICT (batch_id, normalized_relative_path) DO NOTHING
                """,
                (
                    batch["id"],
                    str(image_path),
                    normalized,
                    image_path.name,
                    _SOURCE_MACHINE,
                ),
            )


def _category_id(conn, category_name: str) -> int:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM asset.categories WHERE name = %s", (category_name,))
        row = cur.fetchone()
    if not row:
        raise ValueError(f"Unknown category: {category_name}")
    return row["id"]


def _decode_image(path: Path) -> dict:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {
            "width": image.width,
            "height": image.height,
            "file_format": (image.format or path.suffix.lstrip(".")).lower(),
        }


def _get_or_create_tag(conn, tag_name: str) -> int | None:
    normalized = tag_name.strip().lower()
    if not normalized:
        return None
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM asset.tags WHERE normalized_name = %s",
            (normalized,),
        )
        row = cur.fetchone()
        if row:
            return row["id"]

        cur.execute(
            """
            INSERT INTO asset.tags (normalized_name, display_name)
            VALUES (%s, %s)
            RETURNING id
            """,
            (normalized, tag_name.strip()),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def _associate_tags(conn, image_id: int, tag_names: list[str]) -> None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for tag_name in tag_names[:5]:
            tag_id = _get_or_create_tag(conn, tag_name)
            if tag_id is None:
                continue

            cur.execute(
                "SELECT COUNT(*) AS count FROM asset.image_tags WHERE image_id = %s",
                (image_id,),
            )
            if cur.fetchone()["count"] >= 5:
                break

            try:
                cur.execute(
                    """
                    INSERT INTO asset.image_tags (image_id, tag_id)
                    VALUES (%s, %s)
                    ON CONFLICT (image_id, tag_id) DO NOTHING
                    """,
                    (image_id, tag_id),
                )
            except psycopg2.Error as exc:
                if exc.pgcode == "23514":
                    break
                raise


def _insert_conflict(
    conn,
    batch_id: int,
    item_id: int,
    image_id: int | None,
    issue_type: str,
    message: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO asset.import_issues (
                batch_id, import_item_id, image_id, issue_type, message
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (batch_id, item_id, image_id, issue_type, message),
        )


def _find_existing_image(conn, sha256: str):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, category_id, capture_type, spectral_type, status
            FROM asset.images
            WHERE sha256 = %s
            """,
            (sha256,),
        )
        return cur.fetchone()


def _insert_image(conn, batch: dict, meta: dict, storage: dict) -> dict:
    category_id = _category_id(conn, batch["category_name"])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO asset.images (
                sha256, storage_key, category_id, capture_type, spectral_type,
                width, height, file_format, byte_size, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ready')
            RETURNING id
            """,
            (
                storage["sha256"],
                storage["storage_key"],
                category_id,
                batch["capture_type"],
                batch["spectral_type"],
                meta["width"],
                meta["height"],
                meta["file_format"],
                storage["byte_size"],
            ),
        )
        return cur.fetchone()


def _insert_image_source(conn, batch: dict, image_id: int, item: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO asset.image_sources (
                image_id, batch_id, source_path, source_filename,
                relative_path, normalized_relative_path, source_machine,
                declared_category_name, declared_capture_type, declared_spectral_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (batch_id, normalized_relative_path) DO NOTHING
            """,
            (
                image_id,
                batch["id"],
                item["source_path"],
                item["source_filename"],
                item["normalized_relative_path"],
                item["normalized_relative_path"],
                _SOURCE_MACHINE,
                batch["category_name"],
                batch.get("capture_type"),
                batch.get("spectral_type"),
            ),
        )


def _process_item(conn, batch: dict, item: dict) -> None:
    item_id = item["id"]
    source_path = Path(item["source_path"])

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE asset.import_items SET status = 'processing', updated_at = NOW() WHERE id = %s",
            (item_id,),
        )

    try:
        meta = _decode_image(source_path)
        storage = store_original(source_path)
        existing = _find_existing_image(conn, storage["sha256"])

        if existing:
            if (
                existing["capture_type"] != batch["capture_type"]
                or existing["spectral_type"] != batch["spectral_type"]
            ):
                _insert_conflict(
                    conn,
                    batch["id"],
                    item_id,
                    existing["id"],
                    "type_conflict",
                    "Duplicate image has different capture/spectral type",
                )

            _insert_image_source(conn, batch, existing["id"], item)
            _associate_tags(conn, existing["id"], batch["tags"])
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE asset.import_items
                    SET status = 'duplicate', image_id = %s, sha256 = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (existing["id"], storage["sha256"], item_id),
                )
            return

        new_image = _insert_image(conn, batch, meta, storage)
        _insert_image_source(conn, batch, new_image["id"], item)
        _associate_tags(conn, new_image["id"], batch["tags"])
        generate_thumbnail(storage["storage_key"])

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE asset.import_items
                SET status = 'imported', image_id = %s, sha256 = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (new_image["id"], storage["sha256"], item_id),
            )
    except Exception as exc:
        logger.exception("Failed to import item %s", item_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE asset.import_items
                SET status = 'failed', error_detail = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (str(exc)[:2000], item_id),
            )


def _finish_batch(conn, batch_id: int) -> None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'imported') AS imported,
                COUNT(*) FILTER (WHERE status = 'duplicate') AS duplicate,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed
            FROM asset.import_items
            WHERE batch_id = %s
            """,
            (batch_id,),
        )
        stats = cur.fetchone()

        if stats["failed"] == 0:
            status = "completed"
        elif stats["imported"] + stats["duplicate"] > 0:
            status = "partial"
        else:
            status = "failed"

        cur.execute(
            """
            UPDATE asset.import_batches
            SET status = %s,
                import_total = %s,
                import_imported = %s,
                import_duplicate = %s,
                import_failed = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                status,
                stats["total"],
                stats["imported"],
                stats["duplicate"],
                stats["failed"],
                batch_id,
            ),
        )


def process_next_queued_batch() -> bool:
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, batch_name, image_path, annotation_path, category_name,
                       capture_type, spectral_type, tags, recursive, status
                FROM asset.import_batches
                WHERE status = 'queued'
                ORDER BY id
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
            batch = cur.fetchone()
            if not batch:
                return False

            cur.execute(
                "UPDATE asset.import_batches SET status = 'importing', updated_at = NOW() WHERE id = %s",
                (batch["id"],),
            )
            conn.commit()

        _ensure_import_items(conn, batch)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, source_path, source_filename, normalized_relative_path, status
                FROM asset.import_items
                WHERE batch_id = %s AND status IN ('pending', 'failed')
                ORDER BY id
                """,
                (batch["id"],),
            )
            items = cur.fetchall()

        for item in items:
            _process_item(conn, batch, item)
            conn.commit()

        try:
            process_annotations_for_batch(conn, batch)
        except Exception:
            logger.exception("Annotation processing failed for batch %s", batch["id"])

        _finish_batch(conn, batch["id"])
        conn.commit()
        logger.info("Finished import batch %s", batch["id"])
        return True
    except Exception:
        conn.rollback()
        logger.exception("Import worker iteration failed")
        return False
    finally:
        conn.close()
