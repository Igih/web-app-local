from pydantic import BaseModel
from typing import Optional
from typing import List

class FolderItem(BaseModel):
    name: str
    is_directory: bool
    path: str
    thumbnail: Optional[str] = None
    is_text: bool = False
    is_xml: bool = False
    is_json: bool = False
    modified_time: Optional[float] = None
    is_corrupted: bool = False
    is_oversized: bool = False

class FolderContent(BaseModel):
    current_path: str
    items: List[FolderItem]
    total_items: int
    has_more: bool
    total_folders: int  # New field
    total_images: int   # New field
    total_texts: int    # New fie

class ImageInfo(BaseModel):
    resolution: Optional[str]
    file_size: Optional[str]
