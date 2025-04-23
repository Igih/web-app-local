from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    role: Optional[str] = None
    id: Optional[int] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class ResetPassword(BaseModel):
    username: str
    new_password: str

class UserInDB(User):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class CreateUser(BaseModel):
    username: str
    password: str
    role: str