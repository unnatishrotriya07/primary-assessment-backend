from pydantic import EmailStr
from typing import Optional
from app.schemas.base_schema import CamelModel

class LoginCredentials(CamelModel):
    email: EmailStr
    password: str

class Token(CamelModel):
    token: str
    token_type: str = "bearer"

class UserInfo(CamelModel):
    id: int
    name: str
    email: EmailStr
    role: str = "admin"

class AuthResponse(CamelModel):
    token: str
    user: UserInfo
