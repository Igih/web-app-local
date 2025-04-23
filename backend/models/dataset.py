from pydantic import BaseModel
from typing import Optional

class DatasetUpdate(BaseModel):
    description: Optional[str] = None
    categories: Optional[str] = None