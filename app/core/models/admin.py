from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from app.db.session import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="admin", nullable=False)
    allowed_features = Column(JSON, nullable=True)
    tenant_id = Column(String, ForeignKey("schools.tenant_id", ondelete="SET NULL"), nullable=True)
