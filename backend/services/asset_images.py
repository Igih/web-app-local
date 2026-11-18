import json
import logging
from typing import Any

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from models.asset_image import AssetImageBatchUpdate, AssetImageUpdate
from models.user import User
from utils.db import db_connection, db_transaction


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CAPTURE_VALUES = {"photo", "hand_drawn"}
SPECTRAL_VALUES = {"visible", "infrared"}


def _type_filter_value(value: str | None, column: str) -> str:
    if value == "unspecified":
        return f"{column} IS NULL"
    return f"{column} = %s"


def _validate_payload(payload: AssetImageUpdate) -> None:
    if payload.capture_type not in (None, "photo", "hand_drawn"):
        raise HTTPException(status_code=400, detail="Invalid capture_type")
    if payload.spectral_type not in (None, "visible", "infrared"):
        raise HTTPException(status_code=400, detail="Invalid spectral_type")
    if payload.tags is not None and len(payload.tags) > 5:
        raise HTTPException(status_code=400, detail="At most 5 tags are allowed")


def _tag_subquery(tag_names: list[str], tag_mode: str, where: list[str], params: list[Any]) -> None:
    if tag_mode == "and":
        where.append(
            """
            (
                SELECT COUNT(DISTINCT t.id)
                FROM asset.image_tags it
                JOIN asset.tags t ON t.id = it.tag_id
                WHERE it.image_id = im.id
                  AND LOWER(t.normalized_name) = ANY(%s)
            ) = %s
            """
        )
        params.extend([tag_names, len(tag_names)])
    else:
        where.append(
            """
            EXISTS (
                SELECT 1
                FROM asset.image_tags it
                JOIN asset.tags t ON t.id = it.tag_id
                WHERE it.image_id = im.id
                  AND LOWER(t.normalized_name) = ANY(%s)
            )
            """
        )
        params.append(tag_names)


async def list_asset_images(
    category: str | None = None,
    capture_type: str | None = None,
    spectral_type: str | None = None,
    tags: str | None = None,
    tag_mode: str = "and",
    source_machine: str | None = None,
    batch_id: int | None = None,
    file_format: str | None = None,
    status: str | None = None,
    min_width: int | None = None,
    min_height: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

    where = ["1 = 1"]
    params: list[Any] = []

    if category:
        where.append("cat.name = %s")
        params.append(category)

    if capture_type:
        if capture_type == "unspecified":
            where.append("im.capture_type IS NULL")
        else:
            where.append("im.capture_type = %s")
            params.append(capture_type)

    if spectral_type:
        if spectral_type == "unspecified":
            where.append("im.spectral_type IS NULL")
        else:
            where.append("im.spectral_type = %s")
            params.append(spectral_type)

    tag_names = [tag.strip().lower() for tag in (tags or "").split(",") if tag.strip()]
    if tag_names:
        _tag_subquery(tag_names, tag_mode, where, params)

    if source_machine:
        where.append(
            """
            EXISTS (
                SELECT 1 FROM asset.image_sources src
                WHERE src.image_id = im.id AND src.source_machine = %s
            )
            """
        )
        params.append(source_machine)

    if batch_id is not None:
        where.append(
            """
            EXISTS (
                SELECT 1 FROM asset.image_sources src
                WHERE src.image_id = im.id AND src.batch_id = %s
            )
            """
        )
        params.append(batch_id)

    if file_format:
        where.append("LOWER(im.file_format) = LOWER(%s)")
        params.append(file_format)
    if status:
        where.append("im.status = %s")
        params.append(status)
    if min_width is not None:
        where.append("im.width >= %s")
        params.append(min_width)
    if min_height is not None:
        where.append("im.height >= %s")
        params.append(min_height)

    where_sql = " AND ".join(where)
    offset = (page - 1) * page_size

    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"SELECT COUNT(*) AS total FROM asset.images im JOIN asset.categories cat ON cat.id = im.category_id WHERE {where_sql}",
                    tuple(params),
                )
                total = cur.fetchone()["total"]

                query = f"""
                    SELECT
                        im.id, im.sha256, im.category_id, cat.name AS category_name,
                        im.capture_type, im.spectral_type, im.width, im.height,
                        im.file_format, im.byte_size, im.status, im.created_at,
                        (
                            SELECT COALESCE(array_agg(t.display_name ORDER BY t.id), '{{}}')
                            FROM asset.image_tags it
                            JOIN asset.tags t ON t.id = it.tag_id
                            WHERE it.image_id = im.id
                        ) AS tags
                    FROM asset.images im
                    JOIN asset.categories cat ON cat.id = im.category_id
                    WHERE {where_sql}
                    ORDER BY im.id
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, tuple(params + [page_size, offset]))
                images = cur.fetchall()

        return {
            "images": images,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list asset images: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list asset images")


def _get_image_detail(cur, image_id: int) -> dict:
    cur.execute(
        """
        SELECT im.*, cat.name AS category_name
        FROM asset.images im
        JOIN asset.categories cat ON cat.id = im.category_id
        WHERE im.id = %s
        """,
        (image_id,),
    )
    image = cur.fetchone()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    cur.execute(
        """
        SELECT t.id, t.normalized_name, t.display_name, t.enabled
        FROM asset.tags t
        JOIN asset.image_tags it ON it.tag_id = t.id
        WHERE it.image_id = %s
        ORDER BY t.id
        """,
        (image_id,),
    )
    image["tags"] = cur.fetchall()

    cur.execute(
        """
        SELECT id, source_path, source_filename, relative_path, source_machine,
               declared_category_name, declared_capture_type, declared_spectral_type
        FROM asset.image_sources
        WHERE image_id = %s
        ORDER BY id
        """,
        (image_id,),
    )
    image["sources"] = cur.fetchall()
    return image


async def get_asset_image(image_id: int, current_user: User) -> dict:
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                return _get_image_detail(cur, image_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get asset image: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get asset image")


def _ensure_tag(cur, tag_name: str) -> int:
    normalized = tag_name.strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")

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
    return row["id"]


def _replace_tags(cur, image_id: int, tag_names: list[str] | None) -> None:
    if tag_names is None:
        return
    if len(tag_names) > 5:
        raise HTTPException(status_code=400, detail="At most 5 tags are allowed")

    cur.execute("DELETE FROM asset.image_tags WHERE image_id = %s", (image_id,))
    for tag_name in tag_names:
        tag_id = _ensure_tag(cur, tag_name)
        cur.execute(
            """
            INSERT INTO asset.image_tags (image_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT (image_id, tag_id) DO NOTHING
            """,
            (image_id, tag_id),
        )


def _category_id(cur, category_name: str | None) -> int | None:
    if category_name is None:
        return None
    cur.execute("SELECT id FROM asset.categories WHERE name = %s", (category_name,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Unknown category")
    return row["id"]


def _audit_image_change(cur, user_id: int | None, image_id: int, before: dict, after: dict) -> None:
    cur.execute(
        """
        INSERT INTO asset.audit_logs (
            user_id, action_type, entity_type, entity_id, before_data, after_data
        )
        VALUES (%s, 'update', 'image', %s, %s::jsonb, %s::jsonb)
        """,
        (
            user_id,
            image_id,
            json.dumps(before, ensure_ascii=False, default=str),
            json.dumps(after, ensure_ascii=False, default=str),
        ),
    )


async def update_asset_image(
    image_id: int,
    payload: AssetImageUpdate,
    current_user: User,
) -> dict:
    _validate_payload(payload)
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, category_id, capture_type, spectral_type FROM asset.images WHERE id = %s",
                    (image_id,),
                )
                image = cur.fetchone()
                if not image:
                    raise HTTPException(status_code=404, detail="Image not found")

                before = dict(image)
                new_category_id = _category_id(cur, payload.category)
                if new_category_id is not None:
                    image["category_id"] = new_category_id
                if payload.capture_type is not None:
                    image["capture_type"] = payload.capture_type
                if payload.spectral_type is not None:
                    image["spectral_type"] = payload.spectral_type
                if image["spectral_type"] and not image["capture_type"]:
                    raise HTTPException(status_code=400, detail="spectral_type requires capture_type")

                cur.execute(
                    """
                    UPDATE asset.images
                    SET category_id = %s, capture_type = %s, spectral_type = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        image["category_id"],
                        image["capture_type"],
                        image["spectral_type"],
                        image_id,
                    ),
                )
                _replace_tags(cur, image_id, payload.tags)
                _audit_image_change(cur, current_user.id, image_id, before, image)
                return _get_image_detail(cur, image_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update asset image: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update asset image")


async def batch_update_asset_images(
    payload: AssetImageBatchUpdate,
    current_user: User,
) -> dict:
    _validate_payload(payload)
    if not payload.image_ids:
        raise HTTPException(status_code=400, detail="image_ids is required")

    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for image_id in payload.image_ids:
                    cur.execute(
                        "SELECT id, category_id, capture_type, spectral_type FROM asset.images WHERE id = %s",
                        (image_id,),
                    )
                    image = cur.fetchone()
                    if not image:
                        raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")

                    before = dict(image)
                    new_category_id = _category_id(cur, payload.category)
                    if new_category_id is not None:
                        image["category_id"] = new_category_id
                    if payload.capture_type is not None:
                        image["capture_type"] = payload.capture_type
                    if payload.spectral_type is not None:
                        image["spectral_type"] = payload.spectral_type
                    if image["spectral_type"] and not image["capture_type"]:
                        raise HTTPException(status_code=400, detail="spectral_type requires capture_type")

                    cur.execute(
                        """
                        UPDATE asset.images
                        SET category_id = %s, capture_type = %s, spectral_type = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (
                            image["category_id"],
                            image["capture_type"],
                            image["spectral_type"],
                            image_id,
                        ),
                    )
                    _replace_tags(cur, image_id, payload.tags)
                    _audit_image_change(cur, current_user.id, image_id, before, image)

        return {
            "message": "Batch update completed",
            "updated": len(payload.image_ids),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to batch update asset images: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to batch update asset images")
