from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException
from models.category import CategoriesShowUpdate
from models.user import User
from services.category import list_categories_show, create_category_show, update_category_show, delete_category_show
from services.auth import admin_required
from typing import Optional, List

router = APIRouter()

@router.get("/categories_show")
async def list(category: Optional[str] = Query(None)):
    return await list_categories_show(category)

@router.post("/categories_show")
async def create(
    images: List[UploadFile] = File(...),
    description: str = Form(None),
    category: str = Form(...),
    count: int = Form(...),
    current_user: User = Depends(admin_required)
):
    return await create_category_show(images, description, category, count, current_user)

@router.put("/categories_show/{category_id}")
async def update(
    category_id: int,
    update: CategoriesShowUpdate,
    current_user: User = Depends(admin_required)
):
    return await update_category_show(category_id, update, current_user)

@router.delete("/categories_show/{category_id}")
async def delete(
    category_id: int,
    current_user: User = Depends(admin_required)
):
    return await delete_category_show(category_id, current_user)