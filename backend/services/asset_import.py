import logging
from collections import defaultdict
from pathlib import Path

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from config import ASSET_INGEST_ROOTS
from models.asset_import import AssetImportScanRequest
from models.asset_enums import is_valid_type_pair
from models.user import User
from services.asset_paths import is_image_file, validate_asset_path
from utils.db import db_connection, db_transaction


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def _validate_scan_request(payload: AssetImportScanRequest) -> tuple[Path, Path | None]:
    if len(payload.tags) > 5:
        raise HTTPException(status_code=400, detail="At most 5 tags are allowed")
    if not is_valid_type_pair(payload.capture_type, payload.spectral_type):
        raise HTTPException(status_code=400, detail="spectral_type requires capture_type")

    image_path = validate_asset_path(payload.image_path, ASSET_INGEST_ROOTS)
    annotation_path = None
    if payload.annotation_path:
        annotation_path = validate_asset_path(payload.annotation_path, ASSET_INGEST_ROOTS)

    return image_path, annotation_path


def _iter_image_paths(root: Path, recursive: bool):
    if root.is_file():
        if is_image_file(root):
            yield root
        return

    if recursive:
        iterator = root.rglob("*")
    else:
        iterator = root.iterdir()

    for path in iterator:
        try:
            if is_image_file(path):
                yield path
        except OSError:
            continue


def _match_annotations(image_paths: list[Path], annotation_path: Path | None) -> dict:
    if annotation_path is None:
        return {"matched": 0, "ambiguous": 0, "unmatched": 0, "total": 0}

    annotation_names: dict[str, list[str]] = defaultdict(list)
    if annotation_path.is_file():
        annotation_names[annotation_path.stem.lower()].append(annotation_path.name)
    else:
        for path in annotation_path.rglob("*"):
            if path.is_file() and not is_image_file(path):
                annotation_names[path.stem.lower()].append(path.name)

    matched = 0
    ambiguous = 0
    unmatched = 0
    for image_path in image_paths:
        candidates = annotation_names.get(image_path.stem.lower(), [])
        if len(candidates) == 1:
            matched += 1
        elif len(candidates) > 1:
            ambiguous += 1
        else:
            unmatched += 1

    return {
        "matched": matched,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
        "total": len(annotation_names),
    }


async def scan_asset_import(payload: AssetImportScanRequest, current_user: User) -> dict:
    image_path, annotation_path = _validate_scan_request(payload)

    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT name FROM asset.categories WHERE name = %s",
                    (payload.category,),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=400, detail="Unknown category")

        image_paths = list(_iter_image_paths(image_path, payload.recursive))
        annotation_summary = _match_annotations(image_paths, annotation_path)

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO asset.import_batches (
                        batch_name, image_path, annotation_path, category_name,
                        capture_type, spectral_type, tags, recursive, status,
                        scan_total, scan_image_count, scan_issue_count
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'awaiting_confirmation', %s, %s, 0)
                    RETURNING id
                    """,
                    (
                        payload.batch_name or image_path.name,
                        str(image_path),
                        str(annotation_path) if annotation_path else None,
                        payload.category,
                        payload.capture_type,
                        payload.spectral_type,
                        payload.tags,
                        payload.recursive,
                        len(image_paths),
                        len(image_paths),
                    ),
                )
                batch = cur.fetchone()

        logger.info("Import scan created by %s: batch %s", current_user.username, batch["id"])
        return {
            "message": "Scan created",
            "batch_id": batch["id"],
            "image_count": len(image_paths),
            "issue_count": 0,
            "annotation_matching": annotation_summary,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to scan asset import: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to scan asset import")


async def get_asset_import_preview(batch_id: int, current_user: User) -> dict:
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, batch_name, image_path, annotation_path, category_name,
                           capture_type, spectral_type, tags, recursive, status,
                           scan_total, scan_image_count, scan_issue_count
                    FROM asset.import_batches
                    WHERE id = %s
                    """,
                    (batch_id,),
                )
                batch = cur.fetchone()
                if not batch:
                    raise HTTPException(status_code=404, detail="Import batch not found")

        annotation_path = Path(batch["annotation_path"]) if batch["annotation_path"] else None
        image_paths = list(_iter_image_paths(Path(batch["image_path"]), batch["recursive"]))
        annotation_summary = _match_annotations(image_paths, annotation_path)

        return {
            "batch": batch,
            "image_count": len(image_paths),
            "issue_count": batch["scan_issue_count"],
            "annotation_matching": annotation_summary,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to load asset import preview: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load import preview")


async def confirm_asset_import(batch_id: int, current_user: User) -> dict:
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE asset.import_batches
                    SET status = 'queued', updated_at = NOW()
                    WHERE id = %s
                      AND status = 'awaiting_confirmation'
                    RETURNING id, status
                    """,
                    (batch_id,),
                )
                batch = cur.fetchone()
                if not batch:
                    raise HTTPException(status_code=409, detail="Batch is not awaiting confirmation")

        logger.info("Import batch queued by %s: %s", current_user.username, batch_id)
        return {"message": "Import queued", "batch_id": batch["id"], "status": batch["status"]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to confirm asset import: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to confirm import")
