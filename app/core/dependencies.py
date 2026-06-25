from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.db.session import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    from app.models.admin import Admin
    from app.models.school import School
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found",
        )
    
    # Resolve school name
    school_name = None
    if admin.tenant_id:
        school = db.query(School).filter(School.tenant_id == admin.tenant_id).first()
        if school:
            school_name = school.name

    return {
        "id": admin.id,
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "allowed_features": admin.allowed_features or [],
        "tenant_id": admin.tenant_id,
        "school_name": school_name
    }

def check_permission(feature_name: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        # Super-Admin (role == "admin" and tenant_id == None) has global access
        if current_user.get("role") == "admin" and current_user.get("tenant_id") is None:
            return current_user
        
        # Admin or Director of a tenant also has full rights within their tenant
        if current_user.get("role") in ("admin", "director"):
            return current_user
            
        allowed = current_user.get("allowed_features", [])
        if feature_name not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: lack of permission for feature '{feature_name}'"
            )
        return current_user
    return dependency

def enforce_super_admin(current_user: dict = Depends(get_current_user)):
    # Super-Admin must have role == "admin" and tenant_id == None
    if current_user.get("role") != "admin" or current_user.get("tenant_id") is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Super-Admin permission required"
        )
    return current_user

def check_admin_role(current_user: dict = Depends(get_current_user)):
    # Allowed for Super-Admins or Director Admins (who can create users for their school)
    if current_user.get("role") != "admin" and current_user.get("role") != "director":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrator role required"
        )
    return current_user
