from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.followup import (
    FollowUpCreate,
    FollowUpListResponse,
    FollowUpResponse,
    VALID_FOLLOWUP_TYPES,
    VALID_INTENTION_LEVELS,
)
from app.services import followup_service, lead_service

router = APIRouter(prefix="/api/v1", tags=["followups"])


# -- Helpers ---------------------------------------------------------------

def _check_lead_access(lead, current_user: User) -> bool:
    """Return True if current_user can access the given lead."""
    if current_user.role in ("admin", "manager"):
        return True
    # counselor: only own leads
    return lead.owner_id == current_user.id


# -- Routes ----------------------------------------------------------------


@router.get("/leads/{lead_id}/followups")
def list_followups(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all follow-ups for a lead."""
    # Verify lead exists
    lead = lead_service.get_lead_by_id(db, lead_id)
    if lead is None:
        return {
            "success": False,
            "error_code": "LEAD_NOT_FOUND",
            "message": "线索不存在",
        }

    # Check permission based on lead ownership
    if not _check_lead_access(lead, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该线索",
        }

    followups = followup_service.list_followups_by_lead(db, lead_id)

    return {
        "success": True,
        "data": [FollowUpResponse(**f).model_dump() for f in followups],
        "message": "ok",
    }


@router.post("/leads/{lead_id}/followups")
def create_followup(
    lead_id: int,
    body: FollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new follow-up for a lead."""
    # Verify lead exists
    lead = lead_service.get_lead_by_id(db, lead_id)
    if lead is None:
        return {
            "success": False,
            "error_code": "LEAD_NOT_FOUND",
            "message": "线索不存在",
        }

    # Check permission based on lead ownership
    if not _check_lead_access(lead, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该线索",
        }

    # Validate followup_type
    if body.followup_type not in VALID_FOLLOWUP_TYPES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的跟进方式: {body.followup_type}，有效值为: {', '.join(sorted(VALID_FOLLOWUP_TYPES))}",
        }

    # Validate intention_level if provided
    if body.intention_level is not None and body.intention_level not in VALID_INTENTION_LEVELS:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的意向等级: {body.intention_level}，有效值为: {', '.join(sorted(VALID_INTENTION_LEVELS))}",
        }

    followup_data = body.model_dump()
    followup = followup_service.create_followup(db, lead_id, followup_data, current_user)

    return {
        "success": True,
        "data": {"id": followup.id},
        "message": "跟进记录已保存",
    }


@router.delete("/followups/{followup_id}")
def delete_followup(
    followup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a follow-up record."""
    followup = followup_service.get_followup_by_id(db, followup_id)
    if followup is None:
        return {
            "success": False,
            "error_code": "FOLLOWUP_NOT_FOUND",
            "message": "跟进记录不存在",
        }

    # Verify the associated lead exists and check permission
    lead = lead_service.get_lead_by_id(db, followup.lead_id)
    if lead is None:
        return {
            "success": False,
            "error_code": "LEAD_NOT_FOUND",
            "message": "线索不存在",
        }

    if not _check_lead_access(lead, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该线索",
        }

    followup_service.delete_followup(db, followup)

    return {
        "success": True,
        "data": None,
        "message": "跟进记录已删除",
    }
