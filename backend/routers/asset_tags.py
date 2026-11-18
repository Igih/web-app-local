from fastapi import APIRouter, Depends

from models.asset_tag import AssetTagCreate, AssetTagUpdate
from models.user import User
from services.asset_tags import (
    create_asset_tag,
    delete_asset_tag,
    list_asset_tags,
    update_asset_tag,
)
from services.auth import admin_required, get_current_active_user


router = APIRouter(prefix="/assets", tags=["asset-tags"])


@router.get("/tags")
async def get_asset_tags(current_user: User = Depends(get_current_active_user)):
    return await list_asset_tags()


@router.post("/tags")
async def post_asset_tag(
    payload: AssetTagCreate,
    current_user: User = Depends(admin_required),
):
    return await create_asset_tag(payload, current_user)


@router.patch("/tags/{tag_id}")
async def patch_asset_tag(
    tag_id: int,
    payload: AssetTagUpdate,
    current_user: User = Depends(admin_required),
):
    return await update_asset_tag(tag_id, payload, current_user)


@router.delete("/tags/{tag_id}")
async def delete_asset_tag_route(
    tag_id: int,
    current_user: User = Depends(admin_required),
):
    return await delete_asset_tag(tag_id, current_user)
