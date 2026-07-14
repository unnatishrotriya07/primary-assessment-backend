from pydantic import EmailStr
from typing import Optional, List
from app.schemas.base_schema import CamelModel

class TeamUserCreate(CamelModel):
    name: str
    email: EmailStr
    password: str
    role: str
    allowed_features: List[str]

class TeamUserUpdate(CamelModel):
    name: Optional[str] = None
    role: Optional[str] = None
    allowed_features: Optional[List[str]] = None
    password: Optional[str] = None

class TeamUserResponse(CamelModel):
    id: int
    name: str
    email: EmailStr
    role: str
    allowed_features: Optional[List[str]] = None
    tenant_id: Optional[str] = None
