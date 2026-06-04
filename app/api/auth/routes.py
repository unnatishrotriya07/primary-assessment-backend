from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.auth_schema import LoginCredentials, AuthResponse, UserInfo
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
def login(credentials: LoginCredentials, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.login(credentials)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    return None

@router.get("/me", response_model=UserInfo)
def get_me(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    auth_service = AuthService(db)
    admin = auth_service.auth_repo.get_admin_by_email(current_user.get("email"))
    if not admin:
        return UserInfo(
            id=1,
            name="Admin Staff",
            email=current_user.get("email"),
            role="admin"
        )
    return UserInfo(
        id=admin.id,
        name=admin.name,
        email=admin.email,
        role="admin"
    )
