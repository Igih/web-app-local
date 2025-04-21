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
UPLOADS_DIR = os.path.join(BASE_STORAGE_DIR, "uploads")
DESCRIPTION_DIR = os.path.join(BASE_STORAGE_DIR, "dataset_descriptions")
IMAGES_DIR = os.path.join(BASE_STORAGE_DIR, "category_images")

os.makedirs(ADMIN_STORAGE_DIR, exist_ok=True)
os.makedirs(USER_STORAGE_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
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

class MarkdownCreate(BaseModel):
    title: str
    content: str

class MarkdownUpdate(BaseModel):
    title: str | None = None
    content: str | None = None

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
                    CREATE TABLE IF NOT EXISTS markdown_documents (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        title VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('public.chinese', title || ' ' || content)) STORED,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;

                    DROP TRIGGER IF EXISTS update_markdown_timestamp ON markdown_documents;
                    CREATE TRIGGER update_markdown_timestamp
                    BEFORE UPDATE ON markdown_documents
                    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS content_tsv_idx 
                    ON markdown_documents USING GIN(content_tsv)
                """)
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

@app.post("/api/upload")
async def upload_zip(
    file: UploadFile = File(...),
    category: str = Form("uncategorized"),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    if not file.filename.endswith(('.zip', '.tar.gz')):
        raise HTTPException(status_code=400, detail="Only .zip or .tar.gz files are allowed")

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

@app.get("/api/pending-uploads")
async def list_pending_uploads(current_user: User = Depends(get_current_active_user)):
    try:
        uploads_dir = os.path.join(UPLOADS_DIR, str(current_user.id))
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

@app.post("/api/upload-from-pending")
async def upload_from_pending(
    filename: str = Form(...),
    category: str = Form("uncategorized"),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    if not filename.endswith(('.zip', '.tar.gz')):
        raise HTTPException(status_code=400, detail="Only .zip or .tar.gz files are allowed")

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

@app.delete("/api/pending-uploads/{filename}")
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
    

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("dist/index.html")