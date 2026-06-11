from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, check_admin_role
from app.schemas.team_schema import TeamUserCreate, TeamUserUpdate, TeamUserResponse
from app.services.team_service import TeamService

router = APIRouter()

@router.get("/", response_model=List[TeamUserResponse])
def get_team_members(
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_admin_role)
):
    service = TeamService(db)
    return service.get_team_members(tenant_id=current_user.get("tenant_id"))

@router.post("/", response_model=TeamUserResponse, status_code=status.HTTP_201_CREATED)
def create_team_member(
    payload: TeamUserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_admin_role)
):
    service = TeamService(db)
    return service.create_team_member(payload, tenant_id=current_user.get("tenant_id"))

@router.put("/{user_id}", response_model=TeamUserResponse)
def update_team_member(
    user_id: int,
    payload: TeamUserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_admin_role)
):
    service = TeamService(db)
    return service.update_team_member(user_id, payload, tenant_id=current_user.get("tenant_id"))

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team_member(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(check_admin_role)
):
    service = TeamService(db)
    service.delete_team_member(
        user_id=user_id,
        current_user_id=current_user.get("id"),
        tenant_id=current_user.get("tenant_id")
    )
    return None
