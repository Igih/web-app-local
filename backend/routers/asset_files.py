from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor

from config import ASSET_ORIGINALS_DIR, ASSET_THUMBNAILS_DIR
from models.user import User
from services.auth import get_current_active_user
from utils.db import db_connection


router = APIRouter(prefix="/assets/files", tags=["asset-files"])


def _storage_key(image_id: int) -> str:
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT storage_key FROM asset.images WHERE id = %s",
                    (image_id,),
                )
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")
        return row["storage_key"]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load image file") from exc


@router.get("/thumbnail/{image_id}")
async def get_thumbnail(
    image_id: int,
    current_user: User = Depends(get_current_active_user),
):
    storage_key = _storage_key(image_id)
    thumbnail = ASSET_THUMBNAILS_DIR / Path(storage_key).with_suffix(".jpg")
    if not thumbnail.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumbnail, media_type="image/jpeg")


@router.get("/original/{image_id}")
async def get_original(
    image_id: int,
    current_user: User = Depends(get_current_active_user),
):
    storage_key = _storage_key(image_id)
    original = ASSET_ORIGINALS_DIR / storage_key
    if not original.exists():
        raise HTTPException(status_code=404, detail="Original image not found")
    return FileResponse(original)
