from typing import List
from sqlalchemy.orm import Session
from app.models.admin import Admin

class TeamRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, tenant_id: str = None) -> List[Admin]:
        query = self.db.query(Admin)
        if tenant_id is not None:
            query = query.filter(Admin.tenant_id == tenant_id)
        return query.all()

    def get_by_id(self, user_id: int, tenant_id: str = None) -> Admin:
        query = self.db.query(Admin).filter(Admin.id == user_id)
        if tenant_id is not None:
            query = query.filter(Admin.tenant_id == tenant_id)
        return query.first()

    def create(self, user_obj: Admin) -> Admin:
        self.db.add(user_obj)
        self.db.commit()
        self.db.refresh(user_obj)
        return user_obj

    def update(self, user_obj: Admin) -> Admin:
        self.db.commit()
        self.db.refresh(user_obj)
        return user_obj

    def delete(self, user_obj: Admin) -> None:
        self.db.delete(user_obj)
        self.db.commit()
