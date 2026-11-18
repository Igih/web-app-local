from typing import Optional

from pydantic import BaseModel


class AssetTag(BaseModel):
    id: int
    normalized_name: str
    display_name: str
    enabled: bool


class AssetTagCreate(BaseModel):
    display_name: str


class AssetTagUpdate(BaseModel):
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
