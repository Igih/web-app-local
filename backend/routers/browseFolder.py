from fastapi import APIRouter, Depends,  Query
from models.user import User
from services.auth import get_current_active_user
from services.browseFolder import browse_folder, get_file_content, get_image_info
from models.browseFolder import FolderContent, ImageInfo

router = APIRouter()

@router.get("/folder", response_model=FolderContent)
async def browse(
    path: str = Query("", description="Relative path to browse"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("name", description="Sort by: name, modified_time"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    current_user: User = Depends(get_current_active_user)
):
    return await browse_folder(path, page, page_size, sort_by, sort_order, current_user)


@router.get("/file/content")
async def get_content(
    path: str = Query(..., description="Relative path to the text, XML, or JSON file"),
    current_user: User = Depends(get_current_active_user)
):
    return await get_file_content(path, current_user)

@router.get("/api/image/info", response_model=ImageInfo)
async def get_info(
    path: str = Query(..., description="Relative path to the image file"),
    current_user: User = Depends(get_current_active_user)
):
    return await get_image_info(path, current_user)