from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import CreateUser, ChangePassword, ResetPassword, User
from services.auth import get_current_active_user, admin_required
from services.user import create_user, change_password, reset_password, search_users

router = APIRouter()

@router.post("/create-user")
async def create_user_route(
    user: CreateUser,
    current_user: User = Depends(admin_required)
):
    return await create_user(user, current_user)

@router.post("/change-password")
async def change_password_route(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user)
):
    return await change_password(password_data, current_user)

@router.post("/reset-password")
async def reset_password_route(
    password_data: ResetPassword,
    current_user: User = Depends(admin_required)
):
    return await reset_password(password_data, current_user)

@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/users/search")
async def search_users_route(
    query: str = Query(None),
    current_user: User = Depends(get_current_active_user)
):
    return await search_users(query, current_user)