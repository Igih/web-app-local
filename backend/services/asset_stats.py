import logging
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from utils.db import db_connection, db_transaction


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

COMBINATIONS = (
    ("photo", "visible"),
    ("photo", "infrared"),
    ("hand_drawn", "visible"),
    ("hand_drawn", "infrared"),
)

TERMINAL_IMPORT_STATUSES = {"completed", "partial", "failed", "stopped"}


def _enrich_import_progress(batch: dict) -> dict:
    status = batch.get("status")
    item_total = int(batch.get("item_total") or 0)
    item_processed = int(batch.get("item_processed") or 0)
    fallback_total = (
        int(batch.get("scan_image_count") or 0)
        or int(batch.get("import_total") or 0)
    )
    total = item_total or fallback_total

    if status in TERMINAL_IMPORT_STATUSES:
        progress_percent = 100
    elif total:
        progress_percent = min(100, round(item_processed / total * 100))
    else:
        progress_percent = 0

    speed_per_second = None
    updated_at = batch.get("updated_at")
    if status in {"queued", "importing"} and updated_at:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(
            0.0,
            (datetime.now(timezone.utc) - updated_at).total_seconds(),
        )
        if elapsed_seconds >= 1:
            speed_per_second = round(item_processed / elapsed_seconds, 2)

    return {
        **batch,
        "item_total": item_total,
        "item_processed": item_processed,
        "progress_total": total,
        "progress_percent": progress_percent,
        "speed_per_second": speed_per_second,
    }


async def get_asset_stats() -> dict:
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, display_name, sort_order
                    FROM asset.categories
                    ORDER BY sort_order, id
                    """
                )
                categories = cur.fetchall()

                cur.execute(
                    """
                    SELECT category_id, capture_type, spectral_type, COUNT(*) AS count
                    FROM asset.images
                    GROUP BY category_id, capture_type, spectral_type
                    """
                )
                rows = cur.fetchall()

                cur.execute("SELECT COUNT(*) AS count FROM asset.images")
                unique_images = cur.fetchone()["count"]

                cur.execute("SELECT COUNT(*) AS count FROM asset.image_sources")
                source_files = cur.fetchone()["count"]

                cur.execute(
                    "SELECT COUNT(*) AS count FROM asset.import_items WHERE status = 'duplicate'"
                )
                duplicates = cur.fetchone()["count"]

                cur.execute(
                    "SELECT COUNT(*) AS count FROM asset.import_items WHERE status = 'failed'"
                )
                damaged = cur.fetchone()["count"]

                cur.execute(
                    "SELECT COUNT(*) AS count FROM asset.import_issues WHERE status = 'open'"
                )
                conflicts = cur.fetchone()["count"]

        lookup: dict[tuple[int, str | None, str | None], int] = defaultdict(int)
        for row in rows:
            lookup[(row["category_id"], row["capture_type"], row["spectral_type"])] = row["count"]

        category_stats = []
        for category in categories:
            combinations = {}
            for capture, spectral in COMBINATIONS:
                key = f"{capture}_{spectral}"
                combinations[key] = lookup.get((category["id"], capture, spectral), 0)

            category_stats.append(
                {
                    "id": category["id"],
                    "name": category["name"],
                    "display_name": category["display_name"],
                    "combinations": combinations,
                    "photo_unspecified": lookup.get((category["id"], "photo", None), 0),
                    "hand_drawn_unspecified": lookup.get(
                        (category["id"], "hand_drawn", None), 0
                    ),
                    "type_unspecified": lookup.get((category["id"], None, None), 0),
                }
            )

        return {
            "categories": category_stats,
            "totals": {
                "unique_images": unique_images,
                "source_files": source_files,
                "duplicates": duplicates,
                "damaged": damaged,
                "conflicts": conflicts,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get asset stats: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get asset stats")


def _build_import_filters(
    status: str | None,
    category_name: str | None,
    search: str | None,
) -> tuple[list[str], list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if status:
        status_values = [value.strip() for value in status.split(",") if value.strip()]
        if status_values:
            placeholders = ", ".join(["%s"] * len(status_values))
            clauses.append(f"b.status IN ({placeholders})")
            params.extend(status_values)

    if category_name:
        clauses.append("b.category_name = %s")
        params.append(category_name)

    if search:
        pattern = f"%{search.strip()}%"
        clauses.append(
            """
            (
                b.batch_name ILIKE %s
                OR CAST(b.id AS TEXT) ILIKE %s
                OR b.image_path ILIKE %s
            )
            """
        )
        params.extend([pattern, pattern, pattern])

    return clauses, params


async def list_asset_imports(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    category_name: str | None = None,
    search: str | None = None,
) -> dict:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    offset = (page - 1) * page_size
    filter_clauses, filter_params = _build_import_filters(
        status, category_name, search
    )
    summary_clauses, summary_params = _build_import_filters(
        None, category_name, search
    )
    filter_sql = ""
    summary_sql = ""
    if filter_clauses:
        filter_sql = " WHERE " + " AND ".join(filter_clauses)
    if summary_clauses:
        summary_sql = " WHERE " + " AND ".join(summary_clauses)

    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"SELECT COUNT(*) AS total FROM asset.import_batches b{filter_sql}",
                    filter_params,
                )
                total = cur.fetchone()["total"]
                cur.execute(
                    f"""
                    SELECT b.id, b.batch_name, b.image_path, b.annotation_path,
                           b.category_name, b.capture_type, b.spectral_type,
                           b.recursive, b.status, b.scan_total,
                           b.scan_image_count, b.scan_issue_count,
                           b.import_total, b.import_imported,
                           b.import_duplicate, b.import_failed,
                           b.created_at, b.updated_at,
                           COALESCE(item.item_total, 0)::INTEGER AS item_total,
                           COALESCE(item.item_processed, 0)::INTEGER AS item_processed,
                           COALESCE(item.item_imported, 0)::INTEGER AS item_imported,
                           COALESCE(item.item_duplicate, 0)::INTEGER AS item_duplicate,
                           COALESCE(item.item_failed, 0)::INTEGER AS item_failed
                    FROM asset.import_batches b
                    LEFT JOIN LATERAL (
                        SELECT
                            COUNT(*) AS item_total,
                            COUNT(*) FILTER (
                                WHERE i.status IN (
                                    'imported', 'duplicate', 'conflict', 'failed', 'skipped'
                                )
                            ) AS item_processed,
                            COUNT(*) FILTER (WHERE i.status = 'imported') AS item_imported,
                            COUNT(*) FILTER (WHERE i.status = 'duplicate') AS item_duplicate,
                            COUNT(*) FILTER (WHERE i.status = 'failed') AS item_failed
                        FROM asset.import_items i
                        WHERE i.batch_id = b.id
                    ) item ON TRUE
                    {filter_sql}
                    ORDER BY b.id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (*filter_params, page_size, offset),
                )
                batches = [_enrich_import_progress(batch) for batch in cur.fetchall()]
                cur.execute(
                    f"""
                    SELECT b.status, COUNT(*) AS count
                    FROM asset.import_batches b
                    {summary_sql}
                    GROUP BY b.status
                    """,
                    summary_params,
                )
                summary = {
                    row["status"]: row["count"]
                    for row in cur.fetchall()
                }

        return {
            "batches": batches,
            "total": total,
            "page": page,
            "page_size": page_size,
            "summary": summary,
            "summary_total": sum(summary.values()),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list asset imports: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list asset imports")


async def get_asset_import(batch_id: int) -> dict:
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, batch_name, image_path, annotation_path, category_name,
                           capture_type, spectral_type, tags, recursive, status,
                           scan_total, scan_image_count, scan_issue_count,
                           import_total, import_imported, import_duplicate, import_failed,
                           error_message, created_at, updated_at
                    FROM asset.import_batches
                    WHERE id = %s
                    """,
                    (batch_id,),
                )
                batch = cur.fetchone()
                if not batch:
                    raise HTTPException(status_code=404, detail="Import batch not found")
        return {"batch": batch}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get asset import: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get asset import")


async def list_asset_import_items(
    batch_id: int,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    offset = (page - 1) * page_size

    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM asset.import_items WHERE batch_id = %s",
                    (batch_id,),
                )
                total = cur.fetchone()["total"]
                cur.execute(
                    """
                    SELECT id, batch_id, image_id, annotation_file_id, source_path,
                           normalized_relative_path, source_filename, source_machine,
                           status, sha256, error_code, error_detail, created_at, updated_at
                    FROM asset.import_items
                    WHERE batch_id = %s
                    ORDER BY id
                    LIMIT %s OFFSET %s
                    """,
                    (batch_id, page_size, offset),
                )
                items = cur.fetchall()

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list asset import items: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list asset import items")


async def retry_asset_import(batch_id: int) -> dict:
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE asset.import_items
                    SET status = 'pending', error_code = NULL, error_detail = NULL,
                        updated_at = NOW()
                    WHERE batch_id = %s AND status IN ('failed', 'skipped')
                    """,
                    (batch_id,),
                )
                failed_count = cur.rowcount

                cur.execute(
                    """
                    UPDATE asset.import_batches
                    SET status = 'queued', error_message = NULL, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                    """,
                    (batch_id,),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Import batch not found")

        return {"message": "Import batch queued for retry", "failed_items": failed_count}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retry asset import: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retry asset import")


async def stop_asset_import(batch_id: int) -> dict:
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE asset.import_batches
                    SET status = 'stopped', updated_at = NOW()
                    WHERE id = %s AND status IN ('queued', 'importing')
                    RETURNING id, status
                    """,
                    (batch_id,),
                )
                batch = cur.fetchone()
                if not batch:
                    raise HTTPException(status_code=409, detail="Batch is not running")

        return {"message": "Import batch stopped", "batch_id": batch["id"], "status": batch["status"]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to stop asset import: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to stop asset import")
