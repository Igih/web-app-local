from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import auth, user, dataset, category, markdown, browseFolder
from config import BASE_STORAGE_DIR, IMAGES_DIR, BROWSE_DIR
import os
from utils.db import init_db_pool

app = FastAPI()

# Create storage directories
os.makedirs(os.path.join(BASE_STORAGE_DIR, "admin"), exist_ok=True)
os.makedirs(os.path.join(BASE_STORAGE_DIR, "users"), exist_ok=True)
os.makedirs(os.path.join(BASE_STORAGE_DIR, "pending_uploads"), exist_ok=True)
os.makedirs(os.path.join(BASE_STORAGE_DIR, "dataset_descriptions"), exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)


# Mount static files
# app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
# app.mount("/static", StaticFiles(directory="dist", html=True), name="app")
app.mount("/category_images", StaticFiles(directory=IMAGES_DIR), name="category_images")
app.mount("/browse_folders", StaticFiles(directory=BROWSE_DIR), name="browse_folders")

init_db_pool()

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(dataset.router, prefix="/api")
app.include_router(category.router, prefix="/api")
app.include_router(markdown.router, prefix="/api")
app.include_router(browseFolder.router, prefix="/api")

# @app.get("/{full_path:path}")
# async def serve_spa(full_path: str):
#     return FileResponse("dist/index.html")