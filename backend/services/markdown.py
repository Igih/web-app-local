from fastapi import HTTPException, status, Depends
from models.markdown import MarkdownCreate, MarkdownUpdate
from services.auth import get_current_active_user
from models.user import User
from utils.db import db_connection, db_transaction
from psycopg2.extras import RealDictCursor
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def create_markdown(
    markdown: MarkdownCreate,
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO markdown_documents (user_id, title, content)
                    VALUES (%s, %s, %s)
                    RETURNING id, user_id, title, content, created_at, updated_at
                    """,
                    (current_user.id, markdown.title, markdown.content)
                )
                new_markdown = cur.fetchone()
        return new_markdown
    except Exception as e:
        logger.error(f"Failed to create markdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create markdown")

async def get_markdowns(current_user: User = Depends(get_current_active_user)):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, title, content, created_at, updated_at
                    FROM markdown_documents
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    """,
                    (current_user.id,)
                )
                markdowns = cur.fetchall()
        # Ensure markdowns is a list; fetchall() should return a list, but be explicit
        return markdowns if isinstance(markdowns, list) else []
    except Exception as e:
        logger.error(f"Failed to fetch markdowns: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch markdowns")

async def update_markdown(
    markdown_id: int,
    markdown: MarkdownUpdate,
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if markdown exists and belongs to user
                cur.execute(
                    """
                    SELECT id, user_id
                    FROM markdown_documents
                    WHERE id = %s AND user_id = %s
                    """,
                    (markdown_id, current_user.id)
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Markdown not found or not authorized")

                # Build update query dynamically
                update_fields = []
                update_values = []
                if markdown.title is not None:
                    update_fields.append("title = %s")
                    update_values.append(markdown.title)
                if markdown.content is not None:
                    update_fields.append("content = %s")
                    update_values.append(markdown.content)

                if not update_fields:
                    raise HTTPException(status_code=400, detail="No fields to update")

                update_values.append(markdown_id)
                update_values.append(current_user.id)
                query = f"""
                    UPDATE markdown_documents
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                    RETURNING id, user_id, title, content, created_at, updated_at
                """
                cur.execute(query, update_values)
                updated_markdown = cur.fetchone()
                if not updated_markdown:
                    raise HTTPException(status_code=404, detail="Markdown not found")
        return updated_markdown
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update markdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update markdown")

async def delete_markdown(
    markdown_id: int,
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    DELETE FROM markdown_documents
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (markdown_id, current_user.id)
                )
                deleted_markdown = cur.fetchone()
                if not deleted_markdown:
                    raise HTTPException(status_code=404, detail="Markdown not found or not authorized")
        return {"message": "Markdown deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete markdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete markdown")