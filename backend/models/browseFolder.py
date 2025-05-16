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
    resolution: Optional[str]
    file_size: Optional[str]
    resolution: str | None = None
    file_size: str | None = None
    is_corrupted: Optional[bool]
    is_oversized: Optional[bool]

class FolderContent(BaseModel):
    current_path: str
    items: List[FolderItem]
    total_items: int
    has_more: bool
    total_folders: int  # New field
    total_images: int   # New field
    total_texts: int    # New fie