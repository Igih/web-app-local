import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080 # 7 days

# Database Configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "mydb"),
    "user": os.getenv("DB_USER", "myzpp"),
    "password": os.getenv("DB_PASSWORD", "my123"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Directory Configuration
BASE_STORAGE_DIR = os.getenv("STORAGE_DIR", "/home/linux/datasets")
ADMIN_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "admin")
USER_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, "users")
UPLOADS_DIR = os.path.join(BASE_STORAGE_DIR, "pending_uploads")
DESCRIPTION_DIR = os.path.join(BASE_STORAGE_DIR, "dataset_descriptions")
IMAGES_DIR = os.path.join(BASE_STORAGE_DIR, "category_images")

BROWSE_DIR = os.getenv("BROWSE_DIR", "/home/linux/Downloads")

# Asset module directory configuration
def _split_paths(raw_value: str) -> list[str]:
    return [path.strip() for path in raw_value.split(",") if path.strip()]


ASSET_ROOT = Path(os.getenv("ASSET_ROOT", "/srv/flower-assets"))
ASSET_INGEST_ROOTS = _split_paths(
    os.getenv("ASSET_INGEST_ROOTS", "/home/linux/Downloads")
)
ASSET_INCOMING_DIR = ASSET_ROOT / "incoming"
ASSET_ORIGINALS_DIR = ASSET_ROOT / "originals"
ASSET_THUMBNAILS_DIR = ASSET_ROOT / "thumbnails"
ASSET_ANNOTATIONS_DIR = ASSET_ROOT / "annotations"
ASSET_QUARANTINE_DIR = ASSET_ROOT / "quarantine"
ASSET_MANIFESTS_DIR = ASSET_ROOT / "manifests"

# Asset quality precheck directories.
ASSET_QUALITY_DIR = ASSET_ROOT / "quality"
ASSET_QUALITY_PREVIEWS_DIR = ASSET_QUALITY_DIR / "previews"
ASSET_QUALITY_EXPORTS_DIR = ASSET_QUALITY_DIR / "exports"

# Quality analysis constants. Keep these explicit so results are reproducible.
QUALITY_PREPROCESS_VERSION = "preprocess_v1"
QUALITY_ALGORITHM_VERSION = "q1_metrics_v1"
QUALITY_ANALYSIS_LONG_SIDE = 1024
QUALITY_PHASH_VERSION = "phash_64_v1"
QUALITY_PHASH_SEARCH_RADIUS = 10

# print(os.getenv("DB_NAME"))
