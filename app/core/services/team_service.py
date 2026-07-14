from typing import List
from sqlalchemy.orm import Session
from app.repositories.team_repository import TeamRepository
from app.schemas.team_schema import TeamUserCreate, TeamUserUpdate
from app.models.admin import Admin
from app.core import security
from app.core.exceptions import EntityNotFoundException
from fastapi import HTTPException

class TeamService:
    def __init__(self, db: Session):
        self.db = db
        self.team_repo = TeamRepository(db)

    def get_team_members(self, tenant_id: str = None) -> List[Admin]:
        return self.team_repo.get_all(tenant_id=tenant_id)

    def create_team_member(self, user_in: TeamUserCreate, tenant_id: str = None) -> Admin:
        # Check if email exists
        existing = self.db.query(Admin).filter(Admin.email == user_in.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already in use by another user.")
            
        hashed_pwd = security.get_password_hash(user_in.password)
        user = Admin(
            name=user_in.name,
            email=user_in.email,
            hashed_password=hashed_pwd,
            role=user_in.role,
            allowed_features=user_in.allowed_features,
            tenant_id=tenant_id
        )
        return self.team_repo.create(user)

    def update_team_member(self, user_id: int, user_in: TeamUserUpdate, tenant_id: str = None) -> Admin:
        user = self.team_repo.get_by_id(user_id, tenant_id=tenant_id)
        if not user:
            raise EntityNotFoundException("Team Member", str(user_id))
            
        if user_in.name is not None:
            user.name = user_in.name
        if user_in.role is not None:
            user.role = user_in.role
        if user_in.allowed_features is not None:
            user.allowed_features = user_in.allowed_features
        if user_in.password is not None and user_in.password.strip() != "":
            user.hashed_password = security.get_password_hash(user_in.password)
            
        return self.team_repo.update(user)

    def delete_team_member(self, user_id: int, current_user_id: int, tenant_id: str = None) -> None:
        user = self.team_repo.get_by_id(user_id, tenant_id=tenant_id)
        if not user:
            raise EntityNotFoundException("Team Member", str(user_id))
        if user.id == current_user_id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account.")
            
        self.team_repo.delete(user)
