from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Depends, status
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
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('root2', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
                hashed_password = get_password_hash("user123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('user', %s, 'user')
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

@app.get("/api/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/api/users/search")
async def search_users(query: str = Query(None), current_user: User = Depends(admin_required)):
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

@app.post("/api/upload")
async def upload_zip(
    file: UploadFile = File(...),
    category: str = Form(...),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    if not file.filename.endswith(('.zip', '.tar.gz')):
        raise HTTPException(status_code=400, detail="Only .zip or .tar.gz files are allowed")

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

        txt_filename = os.path.splitext(file.filename)[0] + ".txt"
        txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)
        if description:
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
                    where_clauses.append("LOWER(d.category) = LOWER(%s)")
                    params.append(category_filter)
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
                raise HTTPException(status_code=400, detail="Categories must not exceed 50 characters")
            update_fields.append("category = %s")
            update_values.append(update.categories)
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_values.append(dataset_id)
        query = f"UPDATE datasets SET {', '.join(update_fields)} WHERE id = %s"

        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(update_values))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Dataset not found")

        txt_filename = os.path.splitext(dataset['filename'])[0] + ".txt"
        txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)
        if update.description is not None:
            with open(txt_file_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(update.description)

        logger.info(f"Updated dataset: {dataset_id}")
        return {"message": "Dataset updated successfully"}
    except Exception as e:
        logger.error(f"Update dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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