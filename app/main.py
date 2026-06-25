import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router
from app.db.session import engine, Base

# Create database tables automatically on startup
try:
    print(f"DEBUG STARTUP: Starting database table creation/migration...", flush=True)
    
    # Import base metadata so all models are recognized
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    print("DEBUG STARTUP: Database tables created/checked successfully.", flush=True)

    # Auto-migrate: ensure columns exist
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        from sqlalchemy import text
        print("DEBUG STARTUP: Running database migrations...", flush=True)
        # Migrate questions table
        try:
            db.execute(text("ALTER TABLE questions ADD COLUMN session VARCHAR"))
            db.commit()
            print("Database migration: Added 'session' column to 'questions' table.", flush=True)
        except Exception as qe:
            db.rollback()
            pass

        try:
            db.execute(text("ALTER TABLE questions ADD COLUMN question_type VARCHAR DEFAULT 'mcq'"))
            db.commit()
            print("Database migration: Added 'question_type' column to 'questions' table.", flush=True)
        except Exception as qe:
            db.rollback()
            pass
            
        # Migrate chapters table
        try:
            db.execute(text("ALTER TABLE chapters ADD COLUMN text_content VARCHAR"))
            db.commit()
            print("Database migration: Added 'text_content' column to 'chapters' table.", flush=True)
        except Exception as ce:
            db.rollback()
            pass

        try:
            db.execute(text("ALTER TABLE chapters ADD COLUMN tenant_id VARCHAR"))
            db.commit()
            print("Database migration: Added 'tenant_id' column to 'chapters' table.", flush=True)
        except Exception as ce:
            db.rollback()
            pass

        # Migrate interviews table
        try:
            db.execute(text("ALTER TABLE interviews ADD COLUMN evaluated_answers JSON"))
            db.commit()
            print("Database migration: Added 'evaluated_answers' column to 'interviews' table.", flush=True)
        except Exception as ie:
            db.rollback()
            pass

        # Migrate admins table for RBAC & Multi-Tenancy
        try:
            db.execute(text("ALTER TABLE admins ADD COLUMN role VARCHAR DEFAULT 'admin'"))
            db.commit()
            print("Database migration: Added 'role' column to 'admins' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        try:
            db.execute(text("ALTER TABLE admins ADD COLUMN allowed_features JSON"))
            db.commit()
            print("Database migration: Added 'allowed_features' column to 'admins' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        try:
            db.execute(text("ALTER TABLE admins ADD COLUMN tenant_id VARCHAR"))
            db.commit()
            print("Database migration: Added 'tenant_id' column to 'admins' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        # Migrate assessments table
        try:
            db.execute(text("ALTER TABLE assessments ADD COLUMN tenant_id VARCHAR"))
            db.commit()
            print("Database migration: Added 'tenant_id' column to 'assessments' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        try:
            db.execute(text("ALTER TABLE assessments ADD COLUMN created_at TIMESTAMP"))
            db.commit()
            print("Database migration: Added 'created_at' column to 'assessments' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        try:
            db.execute(text("ALTER TABLE assessments ADD COLUMN questions_to_ask INTEGER DEFAULT 5"))
            db.commit()
            print("Database migration: Added 'questions_to_ask' column to 'assessments' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        # Migrate questions table tenant_id (if not already handled or needed)
        try:
            db.execute(text("ALTER TABLE questions ADD COLUMN tenant_id VARCHAR"))
            db.commit()
            print("Database migration: Added 'tenant_id' column to 'questions' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass

        # Migrate student_assessments table
        try:
            db.execute(text("ALTER TABLE student_assessments ADD COLUMN tenant_id VARCHAR"))
            db.commit()
            print("Database migration: Added 'tenant_id' column to 'student_assessments' table.", flush=True)
        except Exception as me:
            db.rollback()
            pass
    except Exception as me:
        print(f"DEBUG STARTUP: Database migration failed: {me}", flush=True)
    finally:
        db.close()

    # Auto-seed default admin credentials
    from app.models.admin import Admin
    print("DEBUG STARTUP: Importing security helpers for seeding...", flush=True)
    from app.core.security import get_password_hash
    print("DEBUG STARTUP: Security helpers imported successfully.", flush=True)
    from app.models.class_model import Class
    from app.models.subject import Subject
    from app.models.chapter import Chapter
    from app.models.question import Question
    from app.models.assessment import Assessment

    db = SessionLocal()
    try:
        # Seed default school
        from app.models.school import School
        default_school = db.query(School).filter(School.tenant_id == "SCH-SYSTEM").first()
        if not default_school:
            default_school = School(
                tenant_id="SCH-SYSTEM",
                name="Momentum Central School"
            )
            db.add(default_school)
            db.commit()
            print("Database successfully seeded with default school: Momentum Central School (SCH-SYSTEM)", flush=True)

        print("DEBUG STARTUP: Checking if default admin exists...", flush=True)
        admin_exists = db.query(Admin).filter(Admin.email == "admin@example.com").first()
        if not admin_exists:
            print("DEBUG STARTUP: Admin not found. Creating default admin...", flush=True)
            hashed = get_password_hash("admin123")
            print(f"DEBUG STARTUP: Password hashed successfully: {hashed[:15]}...", flush=True)
            new_admin = Admin(
                name="Admin User",
                email="admin@example.com",
                hashed_password=hashed,
                role="admin",
                allowed_features=["dashboard", "classes", "subjects", "chapters", "questions", "assessments", "reports", "students"],
                tenant_id=None
            )
            db.add(new_admin)
            db.commit()
            print("Database successfully seeded with default administrator (admin@example.com / admin123)", flush=True)
        else:
            print("DEBUG STARTUP: Default admin already exists in the database. Updating attributes if empty...", flush=True)
            dirty = False
            if admin_exists.role != "admin":
                admin_exists.role = "admin"
                dirty = True
            if admin_exists.allowed_features is None:
                admin_exists.allowed_features = ["dashboard", "classes", "subjects", "chapters", "questions", "assessments", "reports", "students"]
                dirty = True
            if dirty:
                db.add(admin_exists)
                db.commit()
                print("Database default admin attributes updated.", flush=True)

        # Seed Grade 1-5 NCERT Syllabus classes, subjects, and chapters if empty
        from app.db.seed_ncert import seed_ncert_data
        seed_ncert_data(db)
    except Exception as se:
        import traceback
        print(f"Database seeding check failed: {se}", flush=True)
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
except Exception as e:
    import traceback
    print(f"Database connection or table creation failed: {e}", flush=True)
    traceback.print_exc()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS origins middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root_health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs"
    }

if __name__ == "__main__":
    # Hot-reload triggered to re-seed database after test execution
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
