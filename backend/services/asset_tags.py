import logging

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from models.asset_tag import AssetTagCreate, AssetTagUpdate
from models.user import User
from utils.db import db_connection, db_transaction


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def _normalize_tag_name(display_name: str) -> str:
    normalized = display_name.strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")
    if len(normalized) > 100:
        raise HTTPException(status_code=400, detail="Tag name must not exceed 100 characters")
    return normalized


def _tag_response(row: dict) -> dict:
    return {
        "id": row["id"],
        "normalized_name": row["normalized_name"],
        "display_name": row["display_name"],
        "enabled": row["enabled"],
    }


async def list_asset_tags() -> dict:
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, normalized_name, display_name, enabled
                    FROM asset.tags
                    WHERE enabled = TRUE
                    ORDER BY id
                    """
                )
                rows = cur.fetchall()

        return {"tags": [_tag_response(row) for row in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list asset tags: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list asset tags")


async def create_asset_tag(payload: AssetTagCreate, current_user: User) -> dict:
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")
    if len(display_name) > 100:
        raise HTTPException(status_code=400, detail="Tag name must not exceed 100 characters")

    normalized_name = _normalize_tag_name(display_name)
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO asset.tags (normalized_name, display_name)
                    VALUES (%s, %s)
                    RETURNING id, normalized_name, display_name, enabled
                    """,
                    (normalized_name, display_name),
                )
                row = cur.fetchone()

        logger.info("Asset tag created by %s: %s", current_user.username, display_name)
        return {"message": "Tag created successfully", "tag": _tag_response(row)}
    except HTTPException:
        raise
    except Exception as exc:
        if getattr(exc, "pgcode", None) == "23505":
            raise HTTPException(status_code=409, detail="Tag already exists")
        logger.error("Failed to create asset tag: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create asset tag")


async def update_asset_tag(
    tag_id: int,
    payload: AssetTagUpdate,
    current_user: User,
) -> dict:
    update_fields: list[str] = []
    update_values: list[object] = []

    if payload.display_name is not None:
        display_name = payload.display_name.strip()
        if not display_name:
            raise HTTPException(status_code=400, detail="Tag name cannot be empty")
        if len(display_name) > 100:
            raise HTTPException(status_code=400, detail="Tag name must not exceed 100 characters")
        update_fields.append("display_name = %s")
        update_values.append(display_name)
        update_fields.append("normalized_name = %s")
        update_values.append(_normalize_tag_name(display_name))

    if payload.enabled is not None:
        update_fields.append("enabled = %s")
        update_values.append(payload.enabled)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_values.append(tag_id)
    set_clause = ", ".join(update_fields)

    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    UPDATE asset.tags
                    SET {set_clause}, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, normalized_name, display_name, enabled
                    """,
                    tuple(update_values),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Tag not found")

        logger.info("Asset tag updated by %s: %s", current_user.username, tag_id)
        return {"message": "Tag updated successfully", "tag": _tag_response(row)}
    except HTTPException:
        raise
    except Exception as exc:
        if getattr(exc, "pgcode", None) == "23505":
            raise HTTPException(status_code=409, detail="Tag already exists")
        logger.error("Failed to update asset tag: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update asset tag")


async def delete_asset_tag(tag_id: int, current_user: User) -> dict:
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE asset.tags
                    SET enabled = FALSE, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                    """,
                    (tag_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Tag not found")

        logger.info("Asset tag disabled by %s: %s", current_user.username, tag_id)
        return {"message": "Tag deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete asset tag: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete asset tag")
