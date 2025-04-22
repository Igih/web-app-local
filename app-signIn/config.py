import os
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database Configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "mydb"),
    "user": os.getenv("DB_USER", "myzpp"),
    "password": os.getenv("DB_PASSWORD", "my123"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Directory Configuration
BASE_STORAGE_DIR = os.getenv("STORAGE_DIR", "/home/linux/codes/datasets")
ADMIN_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "admin")
USER_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "users")
UPLOADS_DIR = os.path.join(BASE_STORAGE_DIR, "uploads")
DESCRIPTION_DIR = os.path.join(BASE_STORAGE_DIR, "dataset_descriptions")
IMAGES_DIR = os.path.join(BASE_STORAGE_DIR, "category_images")

# print(os.getenv("DB_NAME"))