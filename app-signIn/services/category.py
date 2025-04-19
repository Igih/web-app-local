from fastapi import HTTPException, status, Depends
import os
import shutil
import uuid
import logging
from psycopg2.extras import RealDictCursor
from models.category import CategoriesShowUpdate
from models.user import User
from services.auth import admin_required
from utils.db import db_connection, db_transaction
from config import IMAGES_DIR

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def list_categories_show(category: str):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if category:
                    cur.execute(
                        "SELECT id, images, description, category, count FROM categories_show WHERE LOWER(category) = LOWER(%s)",
                        (category,)
                    )
                else:
                    cur.execute("SELECT id, images, description, category, count FROM categories_show")
                categories_show = cur.fetchall()
                for item in categories_show:
                    item['images'] = item.get('images', []) or []
                return {"categories_show": categories_show}
    except Exception as e:
        logger.error(f"Fetch categories error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def create_category_show(images, description: str, category: str, count: int, current_user: User):
    try:
        if len(category) > 50:
            raise HTTPException(status_code=400, detail="Category must not exceed 50 characters")
        if len(images) < 1 or len(images) > 6:
            raise HTTPException(status_code=400, detail="Must upload between 1 and 6 images")

        image_paths = []
        for image in images:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files are allowed")
            file_extension = image.filename.split('.')[-1]
            unique_filename = f"{category}_{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(IMAGES_DIR, unique_filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_paths.append(unique_filename)

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO categories_show (images, description, category, count)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (image_paths, description, category.lower(), count)
                )
                new_category = cur.fetchone()
                if not new_category:
                    raise HTTPException(status_code=500, detail="Failed to create category")

        logger.info(f"Created category: {category} by user {current_user.username}")
        return {"message": "Category created successfully", "id": new_category['id']}
    except Exception as e:
        logger.error(f"Create category error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating category: {str(e)}")

async def update_category_show(
    category_id: int,
    update: CategoriesShowUpdate,
    current_user: User = Depends(admin_required)
):
    try:
        # Check if the category exists
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id FROM categories_show WHERE id = %s",
                    (category_id,)
                )
                category = cur.fetchone()
                if not category:
                    raise HTTPException(status_code=404, detail="Category not found")

        # Prepare the fields to update
        update_fields = []
        update_values = []
        if update.description is not None:
            update_fields.append("description = %s")
            update_values.append(update.description)
        if update.category is not None:
            if len(update.category) > 50:
                raise HTTPException(status_code=400, detail="Category must not exceed 50 characters")
            update_fields.append("category = %s")
            update_values.append(update.category.lower())
        if update.count is not None:
            if not isinstance(update.count, int):
                raise HTTPException(status_code=400, detail="Count must be an integer")
            update_fields.append("count = %s")
            update_values.append(update.count)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update. Ensure 'description', 'category', or 'count' is provided.")

        update_values.append(category_id)
        query = f"UPDATE categories_show SET {', '.join(update_fields)} WHERE id = %s"

        # Execute the update
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(update_values))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Category not found after update attempt")

        logger.info(f"Updated category show: {category_id} by user {current_user.username}")
        return {"message": "Category updated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Update category show error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating category: {str(e)}")

async def delete_category_show(
    category_id: int,
    current_user: User = Depends(admin_required)
):
    try:
        # Fetch the category and its images
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT images FROM categories_show WHERE id = %s",
                    (category_id,)
                )
                category = cur.fetchone()
                if not category:
                    raise HTTPException(status_code=404, detail="Category not found")

        # Delete the category from the database
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM categories_show WHERE id = %s", (category_id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Category not found")

        # Delete associated images from the filesystem
        image_filenames = category.get('images', [])
        for image_filename in image_filenames:
            image_path = os.path.join(IMAGES_DIR, image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

        logger.info(f"Deleted category show: {category_id} by user {current_user.username}")
        return {"message": "Category deleted successfully"}
    except Exception as e:
        logger.error(f"Delete category show error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting category: {str(e)}")
