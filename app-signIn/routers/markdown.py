from fastapi import APIRouter, Depends
from models.user import User
from services.markdown import create_markdown, get_markdowns, update_markdown, delete_markdown
from services.auth import get_current_active_user
from models.markdown import MarkdownCreate, MarkdownUpdate

router = APIRouter()

@router.post("/markdowns")
async def create(
    markdown: MarkdownCreate,
    current_user: User = Depends(get_current_active_user)
):
    return await create_markdown(markdown, current_user)


@router.get("/markdowns")
async def gets(current_user: User = Depends(get_current_active_user)):
    return await get_markdowns(current_user)


@router.put("/markdowns/{markdown_id}")
async def update(
    markdown_id: int,
    markdown: MarkdownUpdate,
    current_user: User = Depends(get_current_active_user)
):
    return await update_markdown(markdown_id, markdown, current_user)


@router.delete("/markdowns/{markdown_id}")
async def delete(
    markdown_id: int,
    current_user: User = Depends(get_current_active_user)
):
    return await delete_markdown(markdown_id, current_user)