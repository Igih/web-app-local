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


app = FastAPI()
STORAGE_DIR = "/home/linux/codes/datasets"
os.makedirs(STORAGE_DIR, exist_ok=True)
IMAGES_DIR = os.path.join(STORAGE_DIR, "category_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # 应该使用更安全的密钥，并从环境变量获取
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
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username, password, role FROM users WHERE username = %s", (username,))
            user_record = cur.fetchone()
            if user_record:
                return UserInDB(**user_record)
    finally:
        release_db_connection(conn)
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

def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
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
                    category VARCHAR(6) NOT NULL
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
            # 添加默认用户
            # 添加默认用户，密码已哈希
            hashed_password = get_password_hash("123456")
            cur.execute("""
                INSERT INTO users (username, password, role)
                VALUES ('zpp', %s, 'admin')
                ON CONFLICT (username) DO NOTHING
            """, (hashed_password,))
            conn.commit()
            logger.info("Database tables initialized")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    finally:
        conn.close()

init_db()


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def release_db_connection(conn):
    conn.close()

class DatasetUpdate(BaseModel):
    description: str | None = None
    categories: str | None = None

class CategoriesShowUpdate(BaseModel):
    description: str | None = None
    category: str | None = None




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

@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    file_path = os.path.join(STORAGE_DIR, file.filename)
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="File already exists")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO datasets (filename, size, description, categories) VALUES (%s, %s, %s, %s)",
                (file.filename, file_size, None, None)
            )
            conn.commit()
        logger.info(f"Uploaded file: {file.filename}")
        return {"filename": file.filename, "message": "Upload successful"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)

@app.get("/api/datasets")
async def list_datasets(
    category_filter: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 构建基础查询
            base_query = "SELECT filename, size, description, categories FROM datasets"
            count_query = "SELECT COUNT(*) FROM datasets"
            
            # 添加过滤条件
            where_clauses = []
            params = []
            
            if category_filter:
                where_clauses.append("(LOWER(categories) LIKE LOWER(%s) OR categories ILIKE %s)")
                params.extend([f"%{category_filter}%", f"%{category_filter}%"])
            
            # 添加WHERE条件
            if where_clauses:
                where_str = " WHERE " + " AND ".join(where_clauses)
                base_query += where_str
                count_query += where_str
            
            # 获取总数
            cur.execute(count_query, params)
            total = cur.fetchone()['count']
            
            # 添加分页
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
    finally:
        release_db_connection(conn)

@app.get("/api/categories_show")
async def list_categories_show(category: str | None = Query(None)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    "SELECT id, images, description, category FROM categories_show WHERE LOWER(category) = LOWER(%s)",
                    (category,))
            else:
                cur.execute("SELECT id, images, description, category FROM categories_show")
            categories_show = cur.fetchall()
            # 确保 images 字段是数组
            for item in categories_show:
                if 'images' not in item or item['images'] is None:
                    item['images'] = []
                # else:
                #     # 返回完整 URL
                #     item['images'] = [f"/category_images/{img}" for img in item['images']]

            logger.debug(f"Categories fetched: {categories_show}")
        return {"categories_show": categories_show}
    except Exception as e:
        logger.error(f"Fetch categories error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)


@app.put("/api/datasets/{filename}")
async def update_dataset(filename: str, update: DatasetUpdate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
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
            cur.execute(query, tuple(update_values))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="File not found")
            conn.commit()
        logger.info(f"Updated dataset: {filename}")
        return {"message": "Dataset updated successfully"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Update dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)

@app.post("/api/categories_show")
async def create_categories_show(
    images: list[UploadFile] = File(...),
    description: str = Form(None),
    category: str = Form(...)
):
    if len(images) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 images can be uploaded")
    if len(category) > 6:
        raise HTTPException(status_code=400, detail="Category must not exceed 6 characters")
    
    conn = get_db_connection()
    try:
        # 修改为不区分大小写的查询
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM categories_show WHERE LOWER(category) = LOWER(%s)", (category,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Category already exists (case insensitive)")

        image_paths = []
        for idx, image in enumerate(images):
            ext = os.path.splitext(image.filename)[1]
            filename = f"{category.lower()}_{int(time.time())}_{idx}{ext}"  # 文件名也使用小写
            filepath = os.path.join(IMAGES_DIR, filename)
            
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            image_paths.append(filename)
        
        with conn.cursor() as cur:
            # 存储时统一转为小写（可选）
            cur.execute(
                "INSERT INTO categories_show (images, description, category) VALUES (%s, %s, %s) RETURNING id",
                (image_paths, description, category.lower())  # 存储小写形式
            )
            new_id = cur.fetchone()['id']
            conn.commit()
        return {"message": "Category created successfully", "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        for path in image_paths:
            try:
                os.remove(os.path.join(IMAGES_DIR, path))
            except:
                pass
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)

# Add this endpoint to serve category images
@app.get("/category_images/{filename}")
async def get_category_image(filename: str):
    file_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

@app.delete("/api/categories_show/{id}")
async def delete_categories_show(id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories_show WHERE id = %s", (id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Category not found")
            conn.commit()
        logger.info(f"Deleted category with id: {id}")
        return {"message": "Category deleted successfully"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Delete category error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)

@app.delete("/api/datasets/{filename}")
async def delete_dataset(filename: str):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM datasets WHERE filename = %s", (filename,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="File not found in database")
            os.remove(file_path)
            conn.commit()
        logger.info(f"Deleted dataset: {filename}")
        return {"message": "File deleted successfully"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Delete dataset error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
    finally:
        release_db_connection(conn)

@app.get("/api/download/{filename}")
async def download_zip(filename: str):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("dist/index.html")