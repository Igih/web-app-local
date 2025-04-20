from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Body, HTTPException
from fastapi.responses import FileResponse
from models.dataset import DatasetUpdate
from models.user import User
from services.dataset import upload_zip, download_zip, list_datasets, list_my_datasets, update_dataset, delete_dataset, get_dataset_paths
from services.auth import get_current_active_user
from typing import Optional, List

router = APIRouter()

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    category: str = Form("uncategorized"),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    return await upload_zip(file, category, description, current_user)


@router.get("/datasets")
async def list(
    category_filter: Optional[str] = Query(None),
    filename_filter: Optional[str] = Query(None),
    uploader_type: Optional[str] = Query(None, regex="^(admin|user|all)$"),
    username_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    return await list_datasets(category_filter, filename_filter, uploader_type, username_filter, page, page_size)

@router.post("/datasets/paths")
async def get_paths(
    dataset_ids: List[int] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    return await get_dataset_paths(dataset_ids, current_user)

@router.get("/my-datasets")
async def list_my(
    filename_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    return await list_my_datasets(filename_filter, page, page_size, current_user)

@router.put("/datasets/{dataset_id}")
async def update(
    dataset_id: int,
    update: DatasetUpdate,
    current_user: User = Depends(get_current_active_user)
):
    return await update_dataset(dataset_id, update, current_user)

@router.delete("/datasets/{dataset_id}")
async def delete(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user)
):
    return await delete_dataset(dataset_id, current_user)


@router.get("/download/{dataset_id}")
async def download(
    dataset_id: int
):
    return await download_zip(dataset_id)