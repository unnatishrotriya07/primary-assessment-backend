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

    # Auto-migrate: ensure 'session' column exists in 'questions' table
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        from sqlalchemy import text
        print("DEBUG STARTUP: Running database migrations...", flush=True)
        db.execute(text("ALTER TABLE questions ADD COLUMN session VARCHAR"))
        db.commit()
        print("Database migration: Added 'session' column to 'questions' table.", flush=True)
    except Exception as me:
        print(f"DEBUG STARTUP: Migration skipped (column likely already exists: {me})", flush=True)
        # Ignore if the column already exists
        pass
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
        print("DEBUG STARTUP: Checking if default admin exists...", flush=True)
        admin_exists = db.query(Admin).filter(Admin.email == "admin@example.com").first()
        if not admin_exists:
            print("DEBUG STARTUP: Admin not found. Creating default admin...", flush=True)
            hashed = get_password_hash("admin123")
            print(f"DEBUG STARTUP: Password hashed successfully: {hashed[:15]}...", flush=True)
            new_admin = Admin(
                name="Admin User",
                email="admin@example.com",
                hashed_password=hashed
            )
            db.add(new_admin)
            db.commit()
            print("Database successfully seeded with default administrator (admin@example.com / admin123)", flush=True)
        else:
            print("DEBUG STARTUP: Default admin already exists in the database.", flush=True)
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
