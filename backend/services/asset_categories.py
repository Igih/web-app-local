import logging

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from utils.db import db_connection


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def list_asset_categories() -> dict:
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

        return {"categories": categories}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list asset categories: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list asset categories")
