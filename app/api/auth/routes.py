from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.schemas.auth_schema import LoginCredentials, AuthResponse, UserInfo, SchoolSignupRequest
from app.core.services.auth_service import AuthService

router = APIRouter()

@router.post("/signup", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def signup(payload: SchoolSignupRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        return auth_service.register_school(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=AuthResponse)
def login(credentials: LoginCredentials, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.login(credentials)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    return None

@router.get("/me", response_model=UserInfo)
def get_me(current_user: dict = Depends(get_current_user)):
    return UserInfo(
        id=current_user.get("id"),
        name=current_user.get("name"),
        email=current_user.get("email"),
        role=current_user.get("role"),
        allowed_features=current_user.get("allowed_features"),
        tenant_id=current_user.get("tenant_id"),
        school_name=current_user.get("school_name")
    )
