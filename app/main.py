import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router
from app.db.bootstrap import ensure_db_ready, run_seeds
from app.infrastructure.logging import setup_logging

# Structured JSON logging (CloudWatch-ready); idempotent.
setup_logging()

# Bring the schema to the latest Alembic revision, then (dev only) seed baseline data.
# In production this is a no-op: CI runs `alembic upgrade head` before deploy.
ensure_db_ready()
run_seeds()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS origins middleware. Origins come from BACKEND_CORS_ORIGINS env (SSM on AWS).
# A dev-only regex keeps localhost convenience without allowing wildcard origins in prod.
if settings.BACKEND_CORS_ORIGINS:
    dev_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_origin_regex=dev_origin_regex if settings.APP_ENV == "development" else None,
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
