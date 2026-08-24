"""Lead draft router — query, confirm, and discard lead drafts."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.lead_draft import (
    LeadDraftConfirmRequest,
    LeadDraftResponse,
    LeadDraftUpdateRequest,
)
from app.services import lead_draft_service, resume_batch_service

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

    # v0.2.1: batch drafts arrive as ready/needs_review; `pending` is the
    # legacy single-import status and must keep working.
    if draft.status not in lead_draft_service.CONFIRMABLE_STATUSES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "该草稿已确认或已丢弃，不可重复操作",
        }
    if draft.confirmed_lead_id is not None:
        return {
            "success": False,
            "error_code": "ALREADY_CONFIRMED",
            "message": "该草稿已生成线索，不可重复确认",
        }

    confirm_data = body.model_dump()

    # Duplicate guard for batch drafts. The single-resume flow keeps its
    # original behaviour so v0.2.0 usage is unaffected.
    if draft.batch_id is not None:
        phone = confirm_data.get("phone") or draft.phone
        duplicate = resume_batch_service.find_duplicate_lead(db, phone)
        if duplicate:
            return {
                "success": False,
                "error_code": "DUPLICATE_PHONE",
                "message": "系统中已存在相同手机号线索",
                "data": duplicate,
            }

    lead = lead_draft_service.confirm_draft(db, draft, confirm_data, current_user)

    if draft.batch_id is not None:
        batch = resume_batch_service.get_batch(db, draft.batch_id)
        if batch is not None:
            resume_batch_service.refresh_batch_counters(db, batch)

    return {
        "success": True,
        "data": {"lead_id": lead.id},
        "message": "已生成正式线索",
    }


@router.put("/{draft_id}")
def update_lead_draft(
    draft_id: int,
    body: LeadDraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply a human review correction to a draft.

    Once a name and a valid phone are present — and the phone is not already
    in the CRM — the draft is promoted to `ready` and becomes confirmable.
    """
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

    if draft.status not in lead_draft_service.EDITABLE_STATUSES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "该草稿已确认或已丢弃，不可编辑",
        }

    update_data = body.model_dump(exclude_unset=True)
    draft = lead_draft_service.update_draft(db, draft, update_data)

    if draft.batch_id is not None:
        batch = resume_batch_service.get_batch(db, draft.batch_id)
        if batch is not None:
            resume_batch_service.refresh_batch_counters(db, batch)

    return {
        "success": True,
        "data": LeadDraftResponse.model_validate(draft).model_dump(),
        "message": "草稿已更新",
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

    if draft.status not in lead_draft_service.EDITABLE_STATUSES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "只能丢弃待确认的草稿",
        }

    lead_draft_service.discard_draft(db, draft)

    if draft.batch_id is not None:
        batch = resume_batch_service.get_batch(db, draft.batch_id)
        if batch is not None:
            resume_batch_service.refresh_batch_counters(db, batch)

    return {
        "success": True,
        "data": None,
        "message": "线索草稿已丢弃",
    }
