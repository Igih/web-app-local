from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Depends, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import os
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import base64  
import time
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from psycopg2.pool import SimpleConnectionPool
from tenacity import retry, stop_after_attempt, wait_fixed
from contextlib import contextmanager


app = FastAPI()
STORAGE_DIR = "/home/linux/codes/datasets"
os.makedirs(STORAGE_DIR, exist_ok=True)
DESCRIPTION_DIR = os.path.join(STORAGE_DIR, "dataset_descriptions")
os.makedirs(DESCRIPTION_DIR, exist_ok=True)
IMAGES_DIR = os.path.join(STORAGE_DIR, "category_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# JWT Configuration
SECRET_KEY = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2"  # 应该使用更安全的密钥，并从环境变量获取
# SECRET_KEY = "your-secret-key-here"  # 应该使用更安全的密钥，并从环境变量获取
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

class UserInDB(User):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# Utility functions
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def get_user(username: str):
    try:
        with db_connection() as conn:  # 使用只读上下文管理器
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT username, password, role FROM users WHERE username = %s", (username,))
                user_record = cur.fetchone()
                if user_record:
                    return UserInDB(**user_record)
        return None
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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


# 在全局范围内初始化连接池
try:
    DB_POOL = SimpleConnectionPool(minconn=1, maxconn=20, **DB_CONFIG)
    logger.info("Connection pool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize connection pool: {str(e)}")
    raise

# 修改获取连接的函数
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_db_connection():
    return DB_POOL.getconn()

def get_db_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)

# 修改释放连接的函数
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

# 已有的写操作事务管理器保持不变
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

# 新增只读操作上下文管理器
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
                # 创建表结构
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS datasets (
                        filename VARCHAR PRIMARY KEY,
                        size BIGINT NOT NULL,
                        description TEXT,
                        categories VARCHAR(50)
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS categories_show (
                        id SERIAL PRIMARY KEY,
                        images TEXT[] NOT NULL,
                        description TEXT,
                        category VARCHAR(6) NOT NULL,
                        count INTEGER NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(100) NOT NULL,
                        role VARCHAR(10) NOT NULL DEFAULT 'user'
                    )
                """)
                # # 添加默认用户
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

class DatasetUpdate(BaseModel):
    description: str | None = None
    categories: str | None = None

class CategoriesShowUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    count: int | None = None



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


# 添加登录接口
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
            "role": authenticated_user.role
        },
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/api/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

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
                # 确保 images 字段是数组
                for item in categories_show:
                    if 'images' not in item or item['images'] is None:
                        item['images'] = []
                    # 可选：返回完整图片 URL
                    # item['images'] = [f"/category_images/{img}" for img in item['images']]

                logger.debug(f"Categories fetched: {categories_show}")
            return {"categories_show": categories_show}
    except Exception as e:
        logger.error(f"Fetch categories error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    file_path = os.path.join(STORAGE_DIR, file.filename)
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="File already exists")
    
    temp_path = file_path + ".tmp"
    try:
        # 先保存文件到临时路径
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(temp_path)
        
        # 使用事务上下文管理器
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO datasets (filename, size, description, categories) VALUES (%s, %s, %s, %s)",
                    (file.filename, file_size, None, None)
                )
        
        # 文件操作成功后移动到最终路径
        shutil.move(temp_path, file_path)
        
        logger.info(f"Uploaded file: {file.filename}")
        return {"filename": file.filename, "message": "Upload successful"}
    except psycopg2.Error as db_error:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Database error during upload: {str(db_error)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
    except OSError as os_error:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"File operation error: {str(os_error)}")
        raise HTTPException(status_code=500, detail=f"File operation error: {str(os_error)}")

@app.get("/api/datasets")
async def list_datasets(
    category_filter: str | None = Query(None),
    filename_filter: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    try:
        with db_connection() as conn:  # 使用只读上下文管理器
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                base_query = "SELECT filename, size, description, categories FROM datasets"
                count_query = "SELECT COUNT(*) FROM datasets"
                where_clauses = []
                params = []
                
                if category_filter:
                    where_clauses.append("(LOWER(categories) LIKE LOWER(%s) OR categories ILIKE %s)")
                    params.extend([f"%{category_filter}%", f"%{category_filter}%"])
                
                if filename_filter:  # 添加文件名模糊搜索
                    where_clauses.append("LOWER(filename) LIKE LOWER(%s)")
                    params.append(f"%{filename_filter}%")
                
                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)
                    base_query += where_str
                    count_query += where_str
                
                cur.execute(count_query, params)
                total = cur.fetchone()['count']
                
                base_query += " ORDER BY filename LIMIT %s OFFSET %s"
                params.extend([page_size, (page - 1) * page_size])
                
                cur.execute(base_query, params)
                datasets = cur.fetchall()
                
                logger.debug(f"Datasets fetched: {datasets}")
        
        return {
            "datasets": datasets,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"Fetch datasets error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/categories_show")
async def create_categories_show(
    images: list[UploadFile] = File(...),
    description: str = Form(None),
    category: str = Form(...),
    count: int = Form(...)  # 添加 count 参数，要求为整数且必填
):
    if len(images) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 images can be uploaded")
    if len(category) > 6:
        raise HTTPException(status_code=400, detail="Category must not exceed 6 characters")
    
    image_paths = []
    try:
        # 检查类别是否存在（只读）
        with db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM categories_show WHERE LOWER(category) = LOWER(%s)", (category,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Category already exists (case insensitive)")

        # 处理文件上传
        for idx, image in enumerate(images):
            ext = os.path.splitext(image.filename)[1]
            filename = f"{category.lower()}_{int(time.time())}_{idx}{ext}"
            filepath = os.path.join(IMAGES_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_paths.append(filename)
        
        # 插入操作（写），包含 count 字段
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO categories_show (images, description, category, count) VALUES (%s, %s, %s, %s) RETURNING id",
                    (image_paths, description, category.lower(), count)
                )
                new_id = cur.fetchone()['id']
        
        return {"message": "Category created successfully", "id": new_id}
    except HTTPException as e:
        for path in image_paths:
            file_path = os.path.join(IMAGES_DIR, path)
            if os.path.exists(file_path):
                os.remove(file_path)
        raise e
    except Exception as e:
        for path in image_paths:
            file_path = os.path.join(IMAGES_DIR, path)
            if os.path.exists(file_path):
                os.remove(file_path)
        logger.error(f"Create category error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/categories_show/{id}")
async def update_categories_show(
    id: int,
    update: CategoriesShowUpdate,
    # current_user: User = Depends(admin_required)  # Enforces admin-only access
):
    try:
        update_fields = []
        update_values = []
        
        if update.description is not None:
            update_fields.append("description = %s")
            update_values.append(update.description)
        if update.category is not None:
            if len(update.category) > 6:
                raise HTTPException(status_code=400, detail="Category must not exceed 6 characters")
            update_fields.append("category = %s")
            update_values.append(update.category.lower())
        if update.count is not None:
            if not isinstance(update.count, int):
                raise HTTPException(status_code=400, detail="Count must be an integer")
            update_fields.append("count = %s")
            update_values.append(update.count)
            
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_values.append(id)
        query = f"UPDATE categories_show SET {', '.join(update_fields)} WHERE id = %s"
        
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(update_values))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Category not found")
        
        logger.info(f"Updated category show: {id}")
        return {"message": "Category updated successfully"}
    except Exception as e:
        logger.error(f"Update category show error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/datasets/{filename}")
async def update_dataset(filename: str, update: DatasetUpdate):
    file_path = os.path.join(DESCRIPTION_DIR, filename)
    txt_filename = os.path.splitext(filename)[0] + ".txt"  # Remove .zip and add .txt
    txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)

    try:
        update_fields = []
        update_values = []
        if update.description is not None:
            update_fields.append("description = %s")
            update_values.append(update.description)
        if update.categories is not None:
            if len(update.categories) > 50:
                raise HTTPException(status_code=400, detail="Categories must not exceed 50 characters")
            update_fields.append("categories = %s")
            update_values.append(update.categories)
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_values.append(filename)
        query = f"UPDATE datasets SET {', '.join(update_fields)} WHERE filename = %s"
        
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(update_values))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="File not found")
        
        # Save description to .txt file if description is updated
        if update.description is not None:
            with open(txt_file_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(update.description)
            logger.info(f"Saved description to {txt_file_path}")

        logger.info(f"Updated dataset: {filename}")
        return {"message": "Dataset updated successfully"}
    except Exception as e:
        logger.error(f"Update dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Add this endpoint to serve category images
@app.get("/category_images/{filename}")
async def get_category_image(filename: str):
    file_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

@app.delete("/api/categories_show/{id}")
async def delete_categories_show(id: int):
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM categories_show WHERE id = %s", (id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Category not found")
            logger.info(f"Deleted category with id: {id}")
            return {"message": "Category deleted successfully"}
    except Exception as e:
        logger.error(f"Delete category error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/api/datasets/{filename}")
async def delete_dataset(filename: str):
    file_path = os.path.join(STORAGE_DIR, filename)
    txt_filename = os.path.splitext(filename)[0] + ".txt"  # Corresponding .txt file
    txt_file_path = os.path.join(DESCRIPTION_DIR, txt_filename)

    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if the dataset exists in the database
                cur.execute("SELECT filename FROM datasets WHERE filename = %s", (filename,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="File not found in database")
                
                # Delete the database record
                cur.execute("DELETE FROM datasets WHERE filename = %s", (filename,))
                
                # Delete the dataset file (e.g., .zip)
                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    logger.warning(f"File {filename} not found on disk but deleting database record")
                
                # Delete the corresponding .txt file if it exists
                if os.path.exists(txt_file_path):
                    os.remove(txt_file_path)
                    logger.info(f"Deleted corresponding text file: {txt_filename}")
                else:
                    logger.debug(f"No corresponding text file found for {filename}")

        logger.info(f"Deleted dataset: {filename}")
        return {"message": "File and associated text file deleted successfully"}
    except Exception as e:
        logger.error(f"Delete dataset error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@app.get("/api/download/{filename}")
async def download_zip(filename: str):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("dist/index.html")