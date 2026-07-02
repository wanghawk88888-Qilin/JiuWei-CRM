from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, config, dashboard, followups, health, lead_drafts, leads, resume_imports, users
from app.services.auth_service import create_default_admin_if_needed
from app.services.config_service import init_default_configs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and init default admin
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_admin_if_needed(db)
        init_default_configs(db)
    finally:
        db.close()
    yield
    # Shutdown: nothing to clean up for now


def create_app() -> FastAPI:
    app = FastAPI(
        title="JiuWei CRM Backend",
        description="面向成人AI职业教育机构的轻量级招生CRM系统",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(leads.router)
    app.include_router(followups.router)
    app.include_router(resume_imports.router)
    app.include_router(lead_drafts.router)
    app.include_router(config.router)
    app.include_router(dashboard.router)
    app.include_router(users.router)

    return app


app = create_app()


@app.get("/")
async def root():
    return {
        "success": True,
        "message": "JiuWei CRM Backend is running",
    }
