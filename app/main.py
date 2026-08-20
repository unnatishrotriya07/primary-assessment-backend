import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router
from app.db.session import engine, Base

# Create database tables automatically on startup
try:
    print(f"DEBUG STARTUP: Starting database table creation...", flush=True)
    from app.db.session import Base
    Base.metadata.create_all(bind=engine)
    print("DEBUG STARTUP: Database tables checked successfully.", flush=True)
except Exception as e:
    print(f"DEBUG STARTUP: Table check warning: {e}", flush=True)

try:
    from app.db.session import SessionLocal
    print("DEBUG STARTUP: Importing security helpers for seeding...", flush=True)
    from app.core.security import get_password_hash
    print("DEBUG STARTUP: Security helpers imported successfully.", flush=True)
    from app.core.models.class_model import Class
    from app.core.models.subject import Subject
    from app.core.models.chapter import Chapter
    from app.core.models.question import Question
    from app.core.models.assessment import Assessment

    db = SessionLocal()
    try:
        # Seed default school and admin
        from app.core.models.school import School
        from app.core.models.admin import Admin
        default_school = db.query(School).filter(School.tenant_id == "SCH-SYSTEM").first()
        if not default_school:
            default_school = School(
                tenant_id="SCH-SYSTEM",
                name="Proctors Central School"
            )
            db.add(default_school)
            db.commit()
            print("Database successfully seeded with default school: Proctors Central School (SCH-SYSTEM)", flush=True)

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
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS] + [
            "http://192.168.1.12:3000"
        ],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static folder for Content Engine textbook images
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


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
