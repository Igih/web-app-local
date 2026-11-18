from fastapi import APIRouter

from services.asset_categories import list_asset_categories


router = APIRouter(prefix="/assets", tags=["asset-categories"])


@router.get("/categories")
async def get_asset_categories():
    return await list_asset_categories()
