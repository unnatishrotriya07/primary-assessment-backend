from sqlalchemy.orm import Session
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth_schema import LoginCredentials, AuthResponse, UserInfo
from app.models.admin import Admin
from app.core import security
from app.core.exceptions import InvalidCredentialsException

class AuthService:
    def __init__(self, db: Session):
        self.auth_repo = AuthRepository(db)

    def login(self, credentials: LoginCredentials) -> AuthResponse:
        admin = self.auth_repo.get_admin_by_email(credentials.email)
        if not admin or not security.verify_password(credentials.password, admin.hashed_password):
            raise InvalidCredentialsException()

        token = security.create_access_token(subject=admin.email)
        return AuthResponse(
            token=token,
            user=UserInfo(id=admin.id, name=admin.name, email=admin.email)
        )

    def register_admin(self, name: str, email: str, password: str) -> UserInfo:
        hashed_pwd = security.get_password_hash(password)
        admin = Admin(name=name, email=email, hashed_password=hashed_pwd)
        created_admin = self.auth_repo.create_admin(admin)
        return UserInfo(id=created_admin.id, name=created_admin.name, email=created_admin.email)
