from pydantic import BaseModel


class AssetCategory(BaseModel):
    id: int
    name: str
    display_name: str
    sort_order: int
