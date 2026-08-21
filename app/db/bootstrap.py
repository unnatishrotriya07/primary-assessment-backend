"""
Database bootstrap: migrations + dev seeding.

Migrations belong in Alembic. On AWS the CI/CD pipeline runs `alembic upgrade head`
as a one-off ECS task BEFORE deploying; the app itself never performs DDL at boot.

This module exists so local/dev boots stay convenient while keeping production
free of boot-time DDL and of the default-credentials seed.
"""
import logging
import os
from typing import List

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.common.config import settings
from app.common.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.db.seed_ncert import seed_ncert_data
from app.models.admin import Admin
from app.models.school import School

logger = logging.getLogger(__name__)


def _alembic_config() -> "Config":
    from alembic.config import Config

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = Config(os.path.join(project_root, "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def _is_schema_present(db: Session) -> bool:
    """True when every model table already exists (legacy DB created via create_all)."""
    inspector = inspect(db.get_bind())
    existing = set(inspector.get_table_names())
    expected = set(Base.metadata.tables.keys())
    return expected.issubset(existing)


def _stamp_head() -> None:
    from alembic import command

    logger.info("Database schema already present; stamping Alembic to head (legacy DB).")
    command.stamp(_alembic_config(), "head")


def ensure_db_ready() -> None:
    """
    Bring the database to the latest Alembic revision.

    - production: no-op — CI runs `alembic upgrade head` before deploy.
    - fresh DB: runs `alembic upgrade head` (creates schema + stamps).
    - legacy DB (created via create_all, no alembic_version): stamps to head.
    """
    if settings.APP_ENV == "production":
        logger.info(
            "APP_ENV=production: skipping boot-time migrations. "
            "Run `alembic upgrade head` via the deploy pipeline instead."
        )
        return

    from alembic import command

    db = SessionLocal()
    try:
        if _is_schema_present(db):
            _stamp_head()
        else:
            logger.info("Running `alembic upgrade head` on fresh database...")
            command.upgrade(_alembic_config(), "head")
    except Exception as exc:  # pragma: no cover - defensive boot guard
        logger.warning("Database bootstrap failed (%s); app will rely on runtime checks.", exc)
    finally:
        db.close()


def _seed_default_school(db: Session) -> None:
    default_school = db.query(School).filter(School.tenant_id == "SCH-SYSTEM").first()
    if not default_school:
        db.add(School(tenant_id="SCH-SYSTEM", name="Momentum Central School"))
        db.commit()
        logger.info("Seeded default school: Momentum Central School (SCH-SYSTEM)")


def _seed_default_admin(db: Session) -> None:
    admin = db.query(Admin).filter(Admin.email == "admin@example.com").first()
    if admin:
        return
    db.add(
        Admin(
            name="Admin User",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            allowed_features=[
                "dashboard", "classes", "subjects", "chapters", "questions",
                "assessments", "reports", "students",
            ],
            tenant_id=None,
        )
    )
    db.commit()
    logger.warning("Seeded default admin admin@example.com / admin123 — DEVELOPMENT ONLY")


def run_seeds() -> None:
    """
    Seed default school + admin + NCERT syllabus.

    NEVER runs in production. Production data is provisioned via explicit scripts.
    """
    if settings.APP_ENV == "production":
        logger.info("APP_ENV=production: skipping boot-time seeding.")
        return

    db = SessionLocal()
    try:
        _seed_default_school(db)
        _seed_default_admin(db)
        seed_ncert_data(db)
    except Exception as exc:  # pragma: no cover - defensive seed guard
        import traceback

        logger.warning("Database seeding failed (%s):\n%s", exc, traceback.format_exc())
        db.rollback()
    finally:
        db.close()
