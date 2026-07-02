from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.config import CourseResponse, LeadSourceResponse, SystemSettingResponse
from app.services import config_service

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/lead-sources")
def list_lead_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all active lead sources. Available to all authenticated users."""
    sources = config_service.list_lead_sources(db)
    return {
        "success": True,
        "data": [LeadSourceResponse.model_validate(s).model_dump() for s in sources],
        "message": "ok",
    }


@router.get("/courses")
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all active courses. Available to all authenticated users."""
    courses = config_service.list_courses(db)
    return {
        "success": True,
        "data": [CourseResponse.model_validate(c).model_dump() for c in courses],
        "message": "ok",
    }


@router.get("/system-settings")
def list_system_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all system settings. Admin only."""
    if current_user.role != "admin":
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问系统配置",
        }

    settings = config_service.list_system_settings(db)
    return {
        "success": True,
        "data": [SystemSettingResponse.model_validate(s).model_dump() for s in settings],
        "message": "ok",
    }
