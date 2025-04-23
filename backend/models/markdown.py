from pydantic import BaseModel
from typing import Optional

class MarkdownCreate(BaseModel):
    title: str
    content: str

class MarkdownUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

