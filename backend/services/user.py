from fastapi import HTTPException, status
import logging
from psycopg2.extras import RealDictCursor
from models.user import CreateUser, ChangePassword, ResetPassword, User, UserInDB
from services.auth import get_user, get_password_hash, verify_password
from utils.db import db_connection, db_transaction

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def create_user(user: CreateUser, current_user: User):
    try:
        if len(user.username) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must not exceed 50 characters"
            )
        if len(user.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters"
            )
        if user.role not in ["admin", "user"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'admin' or 'user'"
            )

        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT username FROM users WHERE username = %s",
                    (user.username,)
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already exists"
                    )

        hashed_password = get_password_hash(user.password)
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password, role)
                    VALUES (%s, %s, %s)
                    RETURNING id, username, role
                    """,
                    (user.username, hashed_password, user.role)
                )
                new_user = cur.fetchone()
                if not new_user:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user"
                    )

        logger.info(f"Created user: {user.username} by admin: {current_user.username}")
        return {
            "message": "User created successfully",
            "user": {
                "id": new_user["id"],
                "username": new_user["username"],
                "role": new_user["role"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

async def change_password(password_data: ChangePassword, current_user: User):
    try:
        user = get_user(current_user.username)
        if not user or not verify_password(password_data.current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password"
            )

        if len(password_data.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters"
            )

        hashed_new_password = get_password_hash(password_data.new_password)
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "UPDATE users SET password = %s WHERE username = %s",
                    (hashed_new_password, current_user.username)
                )
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update password"
                    )

        logger.info(f"Password changed successfully for user: {current_user.username}")
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error for user {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )

async def reset_password(password_data: ResetPassword, current_user: User):
    try:
        if not password_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is required"
            )
        if len(password_data.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters"
            )

        target_user = get_user(password_data.username)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User does not exist"
            )

        if password_data.username == current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot reset their own password using this endpoint. Use change-password instead."
            )

        hashed_new_password = get_password_hash(password_data.new_password)
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "UPDATE users SET password = %s WHERE username = %s",
                    (hashed_new_password, password_data.username)
                )
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update password"
                    )

        logger.info(f"Password reset for user {password_data.username} by admin {current_user.username}")
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error for user {password_data.username} by admin {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )

async def search_users(query: str, current_user: User):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if query:
                    cur.execute(
                        "SELECT id, username FROM users WHERE LOWER(username) LIKE LOWER(%s) AND role = 'user'",
                        (f"%{query}%",)
                    )
                else:
                    cur.execute("SELECT id, username FROM users WHERE role = 'user'")
                users = cur.fetchall()
                return users
    except Exception as e:
        logger.error(f"Search users error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")