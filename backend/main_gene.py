from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Depends, status, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Dict
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
import mimetypes

app = FastAPI()

# Directory Configuration
BASE_STORAGE_DIR = "/home/linux/codes/datasets"
ADMIN_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "admin")
USER_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "users")
UPLOADS_DIR = os.path.join(BASE_STORAGE_DIR, "uploads")
DESCRIPTION_DIR = os.path.join(BASE_STORAGE_DIR, "dataset_descriptions")
IMAGES_DIR = os.path.join(BASE_STORAGE_DIR, "category_images")
DOWNLOADS_DIR = "/home/linux/Downloads"

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
app.mount("/browse_folders", StaticFiles(directory=DOWNLOADS_DIR), name="browse_folders")

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

class FolderItem(BaseModel):
    name: str
    is_directory: bool
    path: str
    thumbnail: str | None = None
    is_text: bool = False
    is_xml: bool = False
    is_json: bool = False
    modified_time: float | None = None

class FolderContent(BaseModel):
    current_path: str
    items: List[FolderItem]
    total_items: int
    has_more: bool

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

# Database Connection Pool	Database Connection Pool
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

def sanitize_path(input_path: str) -> str:
    base_dir = DOWNLOADS_DIR
    if not input_path.startswith(base_dir):
        full_path = os.path.abspath(os.path.join(base_dir, input_path.lstrip("/")))
    else:
        full_path = os.path.abspath(input_path)
    
    if not full_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Access to path is forbidden")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path does not exist")
    
    return full_path

@app.get("/api/folder", response_model=FolderContent)
async def browse_folder(
    path: str = Query("", description="Relative path to browse"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("name", description="Sort by: name, modified_time"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    current_user: User = Depends(get_current_active_user)
):
    try:
        full_path = sanitize_path(path)
        relative_path = os.path.relpath(full_path, DOWNLOADS_DIR)

        all_items = []
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.txt', '.xml', '.json'}

        # Count total items first to check limit
        total_items = len([item for item in os.listdir(full_path)])
        if total_items > 100000:
            raise HTTPException(status_code=400, detail="Folder contains more than 100,000 items")

        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            rel_item_path = os.path.join(relative_path, item).replace("\\", "/")
            
            is_directory = os.path.isdir(item_path)
            if not is_directory:
                ext = os.path.splitext(item)[1].lower()
                if ext not in allowed_extensions:
                    continue

            thumbnail = None
            is_text = False
            is_xml = False
            is_json = False
            modified_time = os.path.getmtime(item_path)

            if not is_directory:
                ext = os.path.splitext(item)[1].lower()
                if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}:
                    thumbnail = f"/browse_folders/{rel_item_path}"
                elif ext == '.txt':
                    is_text = True
                elif ext == '.xml':
                    is_xml = True
                elif ext == '.json':
                    is_json = True

            all_items.append(FolderItem(
                name=item,
                is_directory=is_directory,
                path=rel_item_path,
                thumbnail=thumbnail,
                is_text=is_text,
                is_xml=is_xml,
                is_json=is_json,
                modified_time=modified_time
            ))

        # Sorting
        if sort_by == "modified_time":
            all_items.sort(key=lambda x: x.modified_time, reverse=(sort_order == "desc"))
        else:  # sort by name
            all_items.sort(key=lambda x: (not x.is_directory, x.name.lower()), reverse=(sort_order == "desc"))

        objectionable_items = [item for item in all_items if any(word in item.name.lower() for word in ["porn", "xxx", "adult"])]
        for item in objectionable_items:
            all_items.remove(item)

        total_items = len(all_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = all_items[start_idx:end_idx]
        has_more = end_idx < total_items

        return FolderContent(
            current_path=relative_path.replace("\\", "/"),
            items=paginated_items,
            total_items=total_items,
            has_more=has_more
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error browsing folder: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/file/content")
async def get_file_content(
    path: str = Query(..., description="Relative path to the text, XML, or JSON file"),
    current_user: User = Depends(get_current_active_user)
):
    try:
        full_path = sanitize_path(path)
        ext = os.path.splitext(full_path)[1].lower()
        if ext not in {'.txt', '.xml', '.json'}:
            raise HTTPException(status_code=400, detail="Only .txt, .xml, and .json files are supported")
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="File not found")

        file_size = os.path.getsize(full_path)
        if file_size > 1_048_576:
            raise HTTPException(status_code=400, detail="File size exceeds 1MB limit")

        with open(full_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return {"content": content}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a valid text, XML, or JSON file")
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
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

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("dist/index.html")