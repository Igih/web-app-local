from fastapi import APIRouter, Depends, Query

from models.asset_image import AssetImageBatchDelete, AssetImageBatchUpdate, AssetImageUpdate
from models.user import User
from services.asset_images import (
    batch_delete_asset_images,
    batch_update_asset_images,
    delete_asset_image,
    get_asset_image,
    list_asset_images,
    update_asset_image,
)
from services.auth import admin_required, get_current_active_user


router = APIRouter(prefix="/assets/images", tags=["asset-images"])


@router.get("")
async def list_images(
    category: str | None = None,
    capture_type: str | None = None,
    spectral_type: str | None = None,
    tags: str | None = None,
    tag_mode: str = Query("and"),
    source_machine: str | None = None,
    batch_id: int | None = None,
    file_format: str | None = None,
    status: str | None = None,
    min_width: int | None = None,
    min_height: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    return await list_asset_images(
        category=category,
        capture_type=capture_type,
        spectral_type=spectral_type,
        tags=tags,
        tag_mode=tag_mode,
        source_machine=source_machine,
        batch_id=batch_id,
        file_format=file_format,
        status=status,
        min_width=min_width,
        min_height=min_height,
        page=page,
        page_size=page_size,
    )


@router.get("/{image_id}")
async def get_image(
    image_id: int,
    current_user: User = Depends(get_current_active_user),
):
    return await get_asset_image(image_id, current_user)


@router.patch("/{image_id}")
async def patch_image(
    image_id: int,
    payload: AssetImageUpdate,
    current_user: User = Depends(admin_required),
):
    return await update_asset_image(image_id, payload, current_user)


@router.post("/batch")
async def patch_images_batch(
    payload: AssetImageBatchUpdate,
    current_user: User = Depends(admin_required),
):
    return await batch_update_asset_images(payload, current_user)


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    current_user: User = Depends(admin_required),
):
    return await delete_asset_image(image_id, current_user)


@router.post("/batch-delete")
async def delete_images_batch(
    payload: AssetImageBatchDelete,
    current_user: User = Depends(admin_required),
):
    return await batch_delete_asset_images(payload, current_user)
