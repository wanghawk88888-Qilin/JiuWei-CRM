"""Lead draft router — query, confirm, and discard lead drafts."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.lead_draft import LeadDraftConfirmRequest, LeadDraftResponse
from app.services import lead_draft_service

router = APIRouter(prefix="/api/v1/lead-drafts", tags=["lead-drafts"])


# -- Helpers ---------------------------------------------------------------

def _check_draft_access(draft, current_user: User) -> bool:
    """Return True if current_user can access the given draft."""
    return lead_draft_service.check_draft_access(draft, current_user)


# -- Routes ----------------------------------------------------------------

@router.get("/{draft_id}")
def get_lead_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get lead draft detail by ID."""
    draft = lead_draft_service.get_lead_draft_by_id(db, draft_id)
    if draft is None:
        return {
            "success": False,
            "error_code": "LEAD_DRAFT_NOT_FOUND",
            "message": "线索草稿不存在",
        }

    if not _check_draft_access(draft, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该线索草稿",
        }

    return {
        "success": True,
        "data": LeadDraftResponse.model_validate(draft).model_dump(),
        "message": "ok",
    }


@router.post("/{draft_id}/confirm")
def confirm_lead_draft(
    draft_id: int,
    body: LeadDraftConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm a lead draft and create a formal Lead."""
    draft = lead_draft_service.get_lead_draft_by_id(db, draft_id)
    if draft is None:
        return {
            "success": False,
            "error_code": "LEAD_DRAFT_NOT_FOUND",
            "message": "线索草稿不存在",
        }

    if not _check_draft_access(draft, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该线索草稿",
        }

    if draft.status != "pending":
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "该草稿已确认或已丢弃，不可重复操作",
        }

    confirm_data = body.model_dump()
    lead = lead_draft_service.confirm_draft(db, draft, confirm_data, current_user)

    return {
        "success": True,
        "data": {"lead_id": lead.id},
        "message": "已生成正式线索",
    }


@router.post("/{draft_id}/discard")
def discard_lead_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Discard a pending lead draft."""
    draft = lead_draft_service.get_lead_draft_by_id(db, draft_id)
    if draft is None:
        return {
            "success": False,
            "error_code": "LEAD_DRAFT_NOT_FOUND",
            "message": "线索草稿不存在",
        }

    if not _check_draft_access(draft, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该线索草稿",
        }

    if draft.status != "pending":
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "只能丢弃待确认的草稿",
        }

    lead_draft_service.discard_draft(db, draft)

    return {
        "success": True,
        "data": None,
        "message": "线索草稿已丢弃",
    }
