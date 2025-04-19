from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Depends, status, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import os
import shutil
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from psycopg2.pool import SimpleConnectionPool
from tenacity import retry, stop_after_attempt, wait_fixed
from contextlib import contextmanager

app = FastAPI()

# Directory Configuration
BASE_STORAGE_DIR = "/home/linux/codes/datasets"
ADMIN_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "admin")
USER_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "users")
DESCRIPTION_DIR = os.path.join(BASE_STORAGE_DIR, "dataset_descriptions")
IMAGES_DIR = os.path.join(BASE_STORAGE_DIR, "category_images")

os.makedirs(ADMIN_STORAGE_DIR, exist_ok=True)
os.makedirs(USER_STORAGE_DIR, exist_ok=True)
os.makedirs(DESCRIPTION_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# JWT Configuration
SECRET_KEY = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

DB_CONFIG = {
    "dbname": "mydb",
    "user": "myzpp",
    "password": "my123",
    "host": "localhost",
    "port": "5432"
}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
app.mount("/static", StaticFiles(directory="dist", html=True), name="app")
app.mount("/category_images", StaticFiles(directory=IMAGES_DIR), name="category_images")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    role: str | None = None
    id: int | None = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class ResetPassword(BaseModel):
    username: str
    new_password: str

class UserInDB(User):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class DatasetUpdate(BaseModel):
    description: str | None = None
    categories: str | None = None

class CategoriesShowUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    count: int | None = None

class CreateUser(BaseModel):
    username: str
    password: str
    role: str

# Utility Functions
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def get_user(username: str):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
                user_record = cur.fetchone()
                if user_record:
                    return UserInDB(**user_record)
        return None
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

async def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# Database Connection Pool
try:
    DB_POOL = SimpleConnectionPool(minconn=1, maxconn=20, **DB_CONFIG)
    logger.info("Connection pool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize connection pool: {str(e)}")
    raise

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_db_connection():
    return DB_POOL.getconn()

def get_db_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)

def release_db_connection(conn):
    try:
        if conn and not conn.closed:
            conn.rollback()
    except Exception as e:
        logger.warning(f"Error rolling back connection: {str(e)}")
    finally:
        if conn:
            DB_POOL.putconn(conn)
            logger.debug("Connection released to pool")

@contextmanager
def db_transaction():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_db_connection(conn)

@contextmanager
def db_connection():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)

def init_db():
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(100) NOT NULL,
                        role VARCHAR(10) NOT NULL DEFAULT 'user'
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS datasets (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        uploader_type VARCHAR(10) NOT NULL,
                        uploader_id INTEGER REFERENCES users(id),
                        category VARCHAR(50) NOT NULL,
                        description TEXT,
                        size BIGINT NOT NULL,
                        path VARCHAR(512) NOT NULL,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS categories_show (
                        id SERIAL PRIMARY KEY,
                        images TEXT[] NOT NULL,
                        description TEXT,
                        category VARCHAR(50) NOT NULL,
                        count INTEGER NOT NULL
                    )
                """)
                hashed_password = get_password_hash("root123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('root1', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
                hashed_password = get_password_hash("root123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('root2', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
                hashed_password = get_password_hash("user123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('user', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

init_db()

# Routes
@app.post("/api/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login")
async def login(user: UserLogin):
    authenticated_user = authenticate_user(user.username, user.password)
    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": authenticated_user.username}, expires_delta=access_token_expires
    )
    return {
        "message": "Login successful",
        "user": {
            "username": authenticated_user.username,
            "role": authenticated_user.role,
            "id": authenticated_user.id
        },
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/api/create-user")
async def create_user(
    user: CreateUser,
    current_user: User = Depends(admin_required)
):
    try:
        # Validate input
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

        # Check for duplicate username
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

        # Hash the password
        hashed_password = get_password_hash(user.password)

        # Insert new user
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

@app.post("/api/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Verify current password
        user = get_user(current_user.username)
        if not user or not verify_password(password_data.current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password"
            )

        # Validate new password (example: minimum length of 6)
        if len(password_data.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters"
            )

        # Hash the new password
        hashed_new_password = get_password_hash(password_data.new_password)

        # Update password in the database
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

@app.post("/api/reset-password")
async def reset_password(
    password_data: ResetPassword,
    current_user: User = Depends(admin_required)
):
    try:
        # Validate input
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

        # Check if the user exists
        target_user = get_user(password_data.username)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User does not exist"
            )

        # Prevent admin from resetting their own password through this endpoint
        if password_data.username == current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot reset their own password using this endpoint. Use change-password instead."
            )

        # Hash the new password
        hashed_new_password = get_password_hash(password_data.new_password)

        # Update password in the database
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

@app.get("/api/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/api/users/search")
async def search_users(query: str = Query(None), current_user: User = Depends(get_current_active_user)):
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

@app.get("/api/categories_show")
async def list_categories_show(category: str | None = Query(None)):
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

@app.post("/api/categories_show")
async def create_category_show(
    images: list[UploadFile] = File(...),
    description: str = Form(None),
    category: str = Form(...),
    count: int = Form(...),
    current_user: User = Depends(admin_required)
):
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
            image_paths.append(unique_filename)  # 只保存文件名

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

@app.put("/api/categories_show/{category_id}")
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

@app.delete("/api/categories_show/{category_id}")
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

@app.post("/api/upload")
async def upload_zip(
    file: UploadFile = File(...),
    category: str = Form("uncategorized"),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    if not file.filename.endswith(('.zip', '.tar.gz')):
        raise HTTPException(status_code=400, detail="Only .zip or .tar.gz files are allowed")

    # Validate category length
    if len(category) > 50:
        raise HTTPException(status_code=400, detail="Category must not exceed 50 characters")

    # Determine storage path based on user role
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

        # Save description to .txt file only for admins (DatasetManager, Data Adjustment)
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

@app.get("/api/datasets")
async def list_datasets(
    category_filter: str | None = Query(None),
    filename_filter: str | None = Query(None),
    uploader_type: str | None = Query(None, regex="^(admin|user|all)$"),
    username_filter: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
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
                    # 修改为部分匹配，使用 LIKE
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

@app.post("/api/datasets/paths")
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

@app.get("/api/my-datasets")
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

@app.put("/api/datasets/{dataset_id}")
async def update_dataset(
    dataset_id: int,
    update: DatasetUpdate,
    current_user: User = Depends(get_current_active_user)
):
    try:
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT uploader_type, uploader_id, filename FROM datasets WHERE id = %s",
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
        if not update_fields:
            logger.warning(f"No fields to update for dataset {dataset_id}. Payload: {update.dict()}")
            raise HTTPException(status_code=400, detail="No fields to update. Ensure 'categories' or 'description' is provided.")

        update_values.append(dataset_id)
        query = f"UPDATE datasets SET {', '.join(update_fields)} WHERE id = %s"

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                logger.debug(f"Executing query: {query} with values: {update_values}")
                cur.execute(query, tuple(update_values))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Dataset not found after update attempt")

        if current_user.role == "admin" and update.description is not None:
            txt_filename = os.path.splitext(dataset['filename'])[0] + ".txt"
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

@app.delete("/api/datasets/{dataset_id}")
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

@app.get("/api/download/{dataset_id}")
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

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("dist/index.html")