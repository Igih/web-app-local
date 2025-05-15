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

class FolderContent(BaseModel):
    current_path: str
    items: List[FolderItem]
    total_items: int
    has_more: bool