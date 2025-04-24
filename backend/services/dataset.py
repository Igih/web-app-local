from fastapi import HTTPException, Form
import os
import shutil
import logging
from models.dataset import DatasetUpdate
from models.user import User
from services.auth import get_current_active_user
from fastapi import Query, Depends, Body
from psycopg2.extras import RealDictCursor
from fastapi.responses import FileResponse
from utils.db import db_connection, db_transaction
from config import ADMIN_STORAGE_DIR, USER_STORAGE_DIR, DESCRIPTION_DIR, UPLOADS_DIR

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def upload_zip(file, category: str, description: str, current_user: User):
    if not file.filename.endswith(('.zip', '.tar.gz', '.rar')):
        raise HTTPException(status_code=400, detail="Only .zip, .tar.gz or .rar files are allowed")

    if len(category) > 50:
        raise HTTPException(status_code=400, detail="Category must not exceed 50 characters")

    if current_user.role == "admin":
        storage_dir = ADMIN_STORAGE_DIR
        uploader_type = "admin"
        uploader_id = None
    else:
        storage_dir = os.path.join(USER_STORAGE_DIR, str(current_user.id))
        os.makedirs(storage_dir, exist_ok=True)
        uploader_type = "user"
        uploader_id = current_user.id

    file_path = os.path.join(storage_dir, file.filename)
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="File already exists")

    temp_path = file_path + ".tmp"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(temp_path)

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO datasets (filename, uploader_type, uploader_id, category, description, size, path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (file.filename, uploader_type, uploader_id, category, description, file_size, file_path)
                )
        shutil.move(temp_path, file_path)

        if current_user.role == "admin" and description:
            txt_filename = os.path.splitext(file.filename)[0] + ".txt"
            txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)
            with open(txt_file_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(description)

        logger.info(f"Uploaded file: {file.filename} by {current_user.username}")
        return {"filename": file.filename, "message": "Upload successful"}
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

async def download_zip(dataset_id: int):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT filename, path FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cur.fetchone()
                if not dataset:
                    raise HTTPException(status_code=404, detail="Dataset not found")
        file_path = dataset['path']
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path, filename=dataset['filename'], media_type="application/octet-stream")
    except Exception as e:
        logger.error(f"Download dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def list_datasets(category_filter, filename_filter, uploader_type, username_filter, page, page_size):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                base_query = """
                    SELECT d.id, d.filename, d.uploader_type, u.username AS uploader_name,
                           d.category, d.description, d.size, d.path, d.upload_date
                    FROM datasets d
                    LEFT JOIN users u ON d.uploader_id = u.id
                """
                count_query = "SELECT COUNT(*) FROM datasets d"
                where_clauses = []
                params = []

                if category_filter:
                    where_clauses.append("LOWER(d.category) LIKE LOWER(%s)")
                    params.append(f"%{category_filter}%")
                if filename_filter:
                    where_clauses.append("LOWER(d.filename) LIKE LOWER(%s)")
                    params.append(f"%{filename_filter}%")
                if uploader_type and uploader_type != "all":
                    where_clauses.append("d.uploader_type = %s")
                    params.append(uploader_type)
                if username_filter:
                    count_query += " LEFT JOIN users u ON d.uploader_id = u.id"
                    where_clauses.append("LOWER(u.username) LIKE LOWER(%s)")
                    params.append(f"%{username_filter}%")

                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)
                    base_query += where_str
                    count_query += where_str

                cur.execute(count_query, params)
                total = cur.fetchone()['count']

                base_query += " ORDER BY d.upload_date DESC LIMIT %s OFFSET %s"
                params.extend([page_size, (page - 1) * page_size])

                cur.execute(base_query, params)
                datasets = cur.fetchall()

                logger.debug(f"Datasets fetched: {len(datasets)}")
        return {
            "datasets": datasets,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"Fetch datasets error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def list_my_datasets(
    filename_filter: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                base_query = """
                    SELECT id, filename, uploader_type, category, description, size, path, upload_date
                    FROM datasets
                    WHERE uploader_type = 'user' AND uploader_id = %s
                """
                count_query = "SELECT COUNT(*) FROM datasets WHERE uploader_type = 'user' AND uploader_id = %s"
                params = [current_user.id]

                if filename_filter:
                    base_query += " AND LOWER(filename) LIKE LOWER(%s)"
                    count_query += " AND LOWER(filename) LIKE LOWER(%s)"
                    params.append(f"%{filename_filter}%")

                cur.execute(count_query, params)
                total = cur.fetchone()['count']

                base_query += " ORDER BY upload_date DESC LIMIT %s OFFSET %s"
                params.extend([page_size, (page - 1) * page_size])

                cur.execute(base_query, params)
                datasets = cur.fetchall()

                logger.debug(f"My datasets fetched: {len(datasets)} for user {current_user.username}")
        return {
            "datasets": datasets,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"Fetch my datasets error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def update_dataset(
    dataset_id: int,
    update: DatasetUpdate,
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT uploader_type, uploader_id, filename, path FROM datasets WHERE id = %s",
                    (dataset_id,)
                )
                dataset = cur.fetchone()
                if not dataset:
                    raise HTTPException(status_code=404, detail="Dataset not found")
                if dataset['uploader_type'] == 'user' and dataset['uploader_id'] != current_user.id and current_user.role != 'admin':
                    raise HTTPException(status_code=403, detail="Not authorized to update this dataset")

        update_fields = []
        update_values = []
        if update.description is not None:
            update_fields.append("description = %s")
            update_values.append(update.description)
        if update.categories is not None:
            if len(update.categories) > 50:
                raise HTTPException(status_code=400, detail="Category must not exceed 50 characters")
            update_fields.append("category = %s")
            update_values.append(update.categories)
        if update.filename is not None:
            if not update.filename:
                raise HTTPException(status_code=400, detail="Filename cannot be empty")
            original_suffix = dataset['filename'].rsplit('.', 1)[-1] if '.' in dataset['filename'] else ''
            input_suffix = update.filename.rsplit('.', 1)[-1] if '.' in update.filename else ''
            allowed_extensions = {'zip', 'tar.gz', 'rar'}
            if original_suffix not in allowed_extensions:
                raise HTTPException(status_code=400, detail="Original filename has an invalid extension")
            # Preserve original suffix if input suffix differs or is missing
            final_filename = update.filename if input_suffix == original_suffix else update.filename.rsplit('.', 1)[0] + '.' + original_suffix
            storage_dir = os.path.dirname(dataset['path'])
            new_file_path = os.path.join(storage_dir, final_filename)
            if os.path.exists(new_file_path):
                raise HTTPException(status_code=400, detail="Filename already exists")
            update_fields.append("filename = %s")
            update_values.append(final_filename)
            update_fields.append("path = %s")
            update_values.append(new_file_path)

        if not update_fields:
            logger.warning(f"No fields to update for dataset {dataset_id}. Payload: {update.dict()}")
            raise HTTPException(status_code=400, detail="No fields to update. Ensure 'categories', 'description', or 'filename' is provided.")

        update_values.append(dataset_id)
        query = f"UPDATE datasets SET {', '.join(update_fields)} WHERE id = %s"

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                logger.debug(f"Executing query: {query} with values: {update_values}")
                cur.execute(query, tuple(update_values))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Dataset not found after update attempt")

        if update.filename is not None:
            # Rename the actual file
            old_file_path = dataset['path']
            final_filename = update_values[update_fields.index("filename = %s")]  # Use the final filename
            new_file_path = os.path.join(storage_dir, final_filename)
            if os.path.exists(old_file_path):
                shutil.move(old_file_path, new_file_path)
            # Rename the description file if it exists
            # old_txt_filename = os.path.splitext(dataset['filename'])[0] + ".txt"
            # new_txt_filename = os.path.splitext(final_filename)[0] + ".txt"
            # old_txt_file_path = os.path.join(DESCRIPTION_DIR, old_txt_filename)
            # new_txt_file_path = os.path.join(DESCRIPTION_DIR, new_txt_filename)
            # if os.path.exists(old_txt_file_path):
            #     shutil.move(old_txt_file_path, new_txt_file_path)

        if current_user.role == "admin" and update.description is not None:
            txt_filename = os.path.splitext(dataset['filename' if update.filename is None else final_filename])[0] + ".txt"
            txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)
            with open(txt_file_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(update.description)

        logger.info(f"Updated dataset: {dataset_id}")
        return {"message": "Dataset updated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during dataset update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

async def delete_dataset(dataset_id: int, current_user: User = Depends(get_current_active_user)):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT uploader_type, uploader_id, filename, path FROM datasets WHERE id = %s",
                    (dataset_id,)
                )
                dataset = cur.fetchone()
                if not dataset:
                    raise HTTPException(status_code=404, detail="Dataset not found")
                if dataset['uploader_type'] == 'user' and dataset['uploader_id'] != current_user.id and current_user.role != 'admin':
                    raise HTTPException(status_code=403, detail="Not authorized to delete this dataset")

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Dataset not found")

        file_path = dataset['path']
        txt_filename = os.path.splitext(dataset['filename'])[0] + ".txt"
        txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)

        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(txt_file_path):
            os.remove(txt_file_path)

        logger.info(f"Deleted dataset: {dataset_id}")
        return {"message": "Dataset deleted successfully"}
    except Exception as e:
        logger.error(f"Delete dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def get_dataset_paths(
    dataset_ids: list[int] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, path
                    FROM datasets
                    WHERE id = ANY(%s)
                    """,
                    (dataset_ids,)
                )
                datasets = cur.fetchall()
                paths = [dataset['path'] for dataset in datasets if dataset['path']]
                return {"paths": paths}
    except Exception as e:
        logger.error(f"Fetch dataset paths error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def list_pending_uploads(current_user: User = Depends(get_current_active_user)):
    try:
        uploads_dir = os.path.join(UPLOADS_DIR, str(current_user.username))
        os.makedirs(uploads_dir, exist_ok=True)
        files = []
        for filename in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                files.append({
                    "filename": filename,
                    "size": file_size,
                    "path": file_path
                })
        logger.debug(f"Pending uploads fetched: {len(files)} for user {current_user.username}")
        return {"files": files}
    except Exception as e:
        logger.error(f"Fetch pending uploads error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching pending uploads: {str(e)}")

async def upload_from_pending(
    filename: str = Form(...),
    category: str = Form("uncategorized"),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    if not filename.endswith(('.zip', '.tar.gz', '.rar')):
        raise HTTPException(status_code=400, detail="Only .zip , .rar or .tar.gz files are allowed")

    if len(category) > 50:
        raise HTTPException(status_code=400, detail="Category must not exceed 50 characters")

    uploads_dir = os.path.join(UPLOADS_DIR, str(current_user.id))
    source_path = os.path.join(uploads_dir, filename)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="File not found in uploads folder")

    storage_dir = os.path.join(USER_STORAGE_DIR, str(current_user.id))
    os.makedirs(storage_dir, exist_ok=True)
    destination_path = os.path.join(storage_dir, filename)

    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM datasets WHERE filename = %s AND uploader_id = %s",
                    (filename, current_user.id)
                )
                if cur.fetchone()['count'] > 0:
                    raise HTTPException(status_code=400, detail="File already exists in datasets")

        file_size = os.path.getsize(source_path)
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO datasets (filename, uploader_type, uploader_id, category, description, size, path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (filename, "user", current_user.id, category, description, file_size, destination_path)
                )
        shutil.copy2(source_path, destination_path)
        os.remove(source_path)

        logger.info(f"Uploaded file from pending: {filename} by {current_user.username}")
        return {"filename": filename, "message": "Upload successful"}
    except Exception as e:
        logger.error(f"Upload from pending error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


async def delete_pending_upload(filename: str, current_user: User = Depends(get_current_active_user)):
    uploads_dir = os.path.join(UPLOADS_DIR, str(current_user.id))
    file_path = os.path.join(uploads_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in uploads folder")
    try:
        os.remove(file_path)
        logger.info(f"Deleted pending upload: {filename} by {current_user.username}")
        return {"message": "File deleted successfully"}
    except Exception as e:
        logger.error(f"Delete pending upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")