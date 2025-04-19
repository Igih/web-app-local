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
