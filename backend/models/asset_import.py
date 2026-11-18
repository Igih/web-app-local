from typing import Optional

from pydantic import BaseModel


class AssetImportScanRequest(BaseModel):
    image_path: str
    category: str
    annotation_path: Optional[str] = None
    capture_type: Optional[str] = None
    spectral_type: Optional[str] = None
    tags: list[str] = []
    recursive: bool = True
    batch_name: Optional[str] = None
