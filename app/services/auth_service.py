from sqlalchemy.orm import Session
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth_schema import LoginCredentials, AuthResponse, UserInfo, SchoolSignupRequest
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

        from app.models.school import School
        school_name = None
        if admin.tenant_id:
            school = self.auth_repo.db.query(School).filter(School.tenant_id == admin.tenant_id).first()
            if school:
                school_name = school.name

        token = security.create_access_token(
            subject=admin.email,
            role=admin.role,
            tenant_id=admin.tenant_id,
            allowed_features=admin.allowed_features
        )
        return AuthResponse(
            token=token,
            user=UserInfo(
                id=admin.id,
                name=admin.name,
                email=admin.email,
                role=admin.role,
                allowed_features=admin.allowed_features or [],
                tenant_id=admin.tenant_id,
                school_name=school_name
            )
        )

    def register_admin(self, name: str, email: str, password: str) -> UserInfo:
        hashed_pwd = security.get_password_hash(password)
        admin = Admin(name=name, email=email, hashed_password=hashed_pwd)
        created_admin = self.auth_repo.create_admin(admin)
        return UserInfo(id=created_admin.id, name=created_admin.name, email=created_admin.email)

    def register_school(self, payload: SchoolSignupRequest) -> UserInfo:
        import random
        import string
        import re
        from app.models.school import School
        
        # Check if email is already registered
        existing_user = self.auth_repo.get_admin_by_email(payload.email)
        if existing_user:
            raise ValueError("Email already registered.")
            
        # Generate alphanumeric school ID (e.g., SCH-7X9B) based on school name
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', payload.school_name).upper()
        prefix = clean_name[:3] if len(clean_name) >= 3 else "SCH"
        
        # Ensure unique tenant_id in loop
        tenant_id = None
        while not tenant_id:
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            candidate = f"{prefix}-{random_part}"
            # Check db
            exists = self.auth_repo.db.query(School).filter(School.tenant_id == candidate).first()
            if not exists:
                tenant_id = candidate
                
        # Create School
        school = School(
            tenant_id=tenant_id,
            name=payload.school_name
        )
        self.auth_repo.db.add(school)
        self.auth_repo.db.commit()
        self.auth_repo.db.refresh(school)
        
        # Create user (default role: Director)
        hashed_pwd = security.get_password_hash(payload.password)
        director = Admin(
            name=payload.name,
            email=payload.email,
            hashed_password=hashed_pwd,
            role="director",
            allowed_features=["dashboard", "students", "classes", "subjects", "chapters", "questions", "assessments", "reports"],  # default features for director
            tenant_id=tenant_id
        )
        
        created_director = self.auth_repo.create_admin(director)
        return UserInfo(
            id=created_director.id,
            name=created_director.name,
            email=created_director.email,
            role=created_director.role,
            tenant_id=created_director.tenant_id,
            school_name=payload.school_name
        )
