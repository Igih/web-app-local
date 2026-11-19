from typing import Optional

from pydantic import BaseModel


class AssetImageUpdate(BaseModel):
    category: Optional[str] = None
    capture_type: Optional[str] = None
    spectral_type: Optional[str] = None
    tags: Optional[list[str]] = None


class AssetImageBatchUpdate(AssetImageUpdate):
    image_ids: list[int]


class AssetImageBatchDelete(BaseModel):
    image_ids: list[int]
