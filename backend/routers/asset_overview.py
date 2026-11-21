from fastapi import APIRouter, Depends, Query

from models.user import User
from services.asset_stats import (
    get_asset_import,
    get_asset_stats,
    list_asset_import_items,
    list_asset_imports,
    retry_asset_import,
    stop_asset_import,
)
from services.auth import admin_required, get_current_active_user


router = APIRouter(prefix="/assets", tags=["asset-overview"])


@router.get("/overview/stats")
async def stats(current_user: User = Depends(get_current_active_user)):
    return await get_asset_stats()


@router.get("/imports")
async def imports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    category_name: str | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    return await list_asset_imports(
        page=page,
        page_size=page_size,
        status=status,
        category_name=category_name,
        search=search,
    )


@router.get("/imports/{batch_id}")
async def import_detail(
    batch_id: int,
    current_user: User = Depends(get_current_active_user),
):
    return await get_asset_import(batch_id)


@router.get("/imports/{batch_id}/items")
async def import_items(
    batch_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    return await list_asset_import_items(batch_id, page, page_size)


@router.post("/imports/{batch_id}/retry")
async def retry_import(
    batch_id: int,
    current_user: User = Depends(admin_required),
):
    return await retry_asset_import(batch_id)


@router.post("/imports/{batch_id}/stop")
async def stop_import(
    batch_id: int,
    current_user: User = Depends(admin_required),
):
    return await stop_asset_import(batch_id)
