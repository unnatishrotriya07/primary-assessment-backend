from sqlalchemy.orm import Session
from app.models.admin import Admin

class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_admin_by_email(self, email: str) -> Admin:
        return self.db.query(Admin).filter(Admin.email == email).first()

    def create_admin(self, admin_obj: Admin) -> Admin:
        self.db.add(admin_obj)
        self.db.commit()
        self.db.refresh(admin_obj)
        return admin_obj
