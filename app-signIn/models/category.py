from pydantic import BaseModel
from typing import Optional

class CategoriesShowUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    count: Optional[int] = None