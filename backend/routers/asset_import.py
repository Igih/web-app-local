from fastapi import APIRouter, Depends

from models.asset_import import AssetImportScanRequest
from models.user import User
from services.asset_import import (
    confirm_asset_import,
    get_asset_import_preview,
    scan_asset_import,
)
from services.auth import admin_required


router = APIRouter(prefix="/assets/imports", tags=["asset-imports"])


@router.post("/scan")
async def scan_import(
    payload: AssetImportScanRequest,
    current_user: User = Depends(admin_required),
):
    return await scan_asset_import(payload, current_user)


@router.get("/{batch_id}/preview")
async def preview_import(
    batch_id: int,
    current_user: User = Depends(admin_required),
):
    return await get_asset_import_preview(batch_id, current_user)


@router.post("/{batch_id}/confirm")
async def confirm_import(
    batch_id: int,
    current_user: User = Depends(admin_required),
):
    return await confirm_asset_import(batch_id, current_user)
