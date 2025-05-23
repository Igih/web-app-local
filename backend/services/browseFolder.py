from fastapi import HTTPException, Query, Depends
import os
from models.browseFolder import FolderContent, FolderItem, ImageInfo
from services.auth import get_current_active_user
from models.user import User
import logging
from config import BROWSE_DIR
from PIL import Image
from functools import lru_cache

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def sanitize_path(input_path: str) -> str:
    base_dir = BROWSE_DIR
    if not input_path.startswith(base_dir):
        full_path = os.path.abspath(os.path.join(base_dir, input_path.lstrip("/")))
    else:
        full_path = os.path.abspath(input_path)
    
    if not full_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Access to path is forbidden")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path does not exist")
    
    return full_path

@lru_cache(maxsize=1000)
def get_image_metadata(full_path: str) -> tuple:
    try:
        file_size = os.path.getsize(full_path)
        modified_timestamp = int(os.path.getmtime(full_path) * 1000)  # Convert to milliseconds
        if file_size > 10_485_760:  # 10MB limit
            return ("Oversized", "Unknown", modified_timestamp)
        with Image.open(full_path) as img:
            width, height = img.size
        file_size_kb = file_size / 1024
        file_size_str = f"{file_size_kb:.2f} KB" if file_size_kb < 1024 else f"{file_size_kb / 1024:.2f} MB"
        return (f"{width}x{height}", file_size_str, modified_timestamp)
    except Exception as e:
        logger.warning(f"Failed to get metadata for {full_path}: {str(e)}")
        modified_timestamp = int(os.path.getmtime(full_path) * 1000) if os.path.exists(full_path) else 0
        return ("Corrupted", "Unknown", modified_timestamp)


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
        relative_path = os.path.relpath(full_path, BROWSE_DIR)

        item_count = 0
        max_items = 100000
        for item in os.scandir(full_path):
            item_count += 1
            if item_count > max_items:
                return FolderContent(
                    current_path=relative_path.replace("\\", "/"),
                    items=[],
                    total_items=item_count,
                    has_more=False,
                    total_folders=0,
                    total_images=0,
                    total_texts=0
                )

        all_items = []
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.txt', '.xml', '.json'}
        folder_count = 0
        image_count = 0
        text_count = 0

        for entry in os.scandir(full_path):
            item_path = os.path.join(full_path, entry.name)
            rel_item_path = os.path.join(relative_path, entry.name).replace("\\", "/")
            
            is_directory = entry.is_dir()
            if not is_directory:
                ext = os.path.splitext(entry.name)[1].lower()
                if ext not in allowed_extensions:
                    continue

            thumbnail = None
            is_text = False
            is_xml = False
            is_json = False
            modified_time = entry.stat().st_mtime
            modified_timestamp = int(modified_time * 1000)  # 转换为毫秒
            is_corrupted = False
            is_oversized = False

            if is_directory:
                folder_count += 1
            else:
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}:
                    file_size = os.path.getsize(item_path)
                    if file_size > 10_485_760:  # 10MB 限制
                        is_oversized = True
                    else:
                        thumbnail = f"/browse_folders/{rel_item_path}?t={modified_timestamp}"  # 添加时间戳
                    image_count += 1
                elif ext == '.txt':
                    is_text = True
                    text_count += 1
                elif ext == '.xml':
                    is_xml = True
                    text_count += 1
                elif ext == '.json':
                    is_json = True
                    text_count += 1

            all_items.append(FolderItem(
                name=entry.name,
                is_directory=is_directory,
                path=rel_item_path,
                thumbnail=thumbnail,
                is_text=is_text,
                is_xml=is_xml,
                is_json=is_json,
                modified_time=modified_time,
                modified_timestamp=modified_timestamp,  # 确保包含
                is_corrupted=is_corrupted,
                is_oversized=is_oversized
            ))

        # 排序和过滤逻辑保持不变
        if sort_by == "modified_time":
            all_items.sort(key=lambda x: x.modified_time, reverse=(sort_order == "desc"))
        else:
            all_items.sort(key=lambda x: (not x.is_directory, x.name.lower()), reverse=(sort_order == "desc"))

        objectionable_items = [item for item in all_items if any(word in item.name.lower() for word in ["porn", "xxx", "adult"])]
        for item in objectionable_items:
            all_items.remove(item)
            if item.is_directory:
                folder_count -= 1
            elif item.thumbnail:
                image_count -= 1
            elif item.is_text or item.is_xml or item.is_json:
                text_count -= 1

        total_items = len(all_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = all_items[start_idx:end_idx]
        has_more = end_idx < total_items

        return FolderContent(
            current_path=relative_path.replace("\\", "/"),
            items=paginated_items,
            total_items=total_items,
            has_more=has_more,
            total_folders=folder_count,
            total_images=image_count,
            total_texts=text_count
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error browsing folder: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def get_image_info(
    path: str = Query(..., description="Relative path to the image file"),
    current_user: User = Depends(get_current_active_user)
):
    try:
        full_path = sanitize_path(path)
        ext = os.path.splitext(full_path)[1].lower()
        if ext not in {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}:
            raise HTTPException(status_code=400, detail="Only image files are supported")
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="File not found")

        resolution, file_size, modified_timestamp = get_image_metadata(full_path)
        if resolution == "Oversized" or resolution == "Corrupted":
            raise HTTPException(status_code=400, detail="Image is oversized or corrupted")

        return ImageInfo(resolution=resolution, file_size=file_size, modified_timestamp=modified_timestamp)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching image info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
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
        elif file_size == 0:
            return {"content": "", "detail": "File is empty"}

        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
            modified_timestamp = int(os.path.getmtime(full_path) * 1000)
            return {"content": content, "modified_timestamp": modified_timestamp}
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is corrupted or not a valid text, XML, or JSON file")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
