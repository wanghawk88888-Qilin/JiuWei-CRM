from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.lead import (
    LeadCreate,
    LeadListItem,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
    VALID_INTENTION_LEVELS,
    VALID_LEAD_STATUSES,
)
from app.services import lead_service

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


# -- Helpers ---------------------------------------------------------------

def _check_lead_access(lead, current_user: User) -> bool:
    """Return True if current_user can access the given lead."""
    if current_user.role in ("admin", "manager"):
        return True
    # counselor: only own leads
    return lead.owner_id == current_user.id


# -- Routes ----------------------------------------------------------------

@router.get("")
def list_leads(
    keyword: str | None = Query(None, description="搜索姓名、手机号、微信（模糊匹配）"),
    status: str | None = Query(None, description="线索状态筛选"),
    source_id: int | None = Query(None, description="来源ID筛选"),
    owner_id: int | None = Query(None, description="负责人ID筛选"),
    page: int = Query(1, ge=1, description="页码，默认1"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，默认20，最大100"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query lead list with search, filter, pagination and role-based permission filtering."""
    # Validate status enum
    if status is not None and status not in VALID_LEAD_STATUSES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的状态值: {status}，有效值为: {', '.join(sorted(VALID_LEAD_STATUSES))}",
        }

    items, total = lead_service.list_leads(
        db,
        current_user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        source_id=source_id,
        owner_id=owner_id,
    )

    return {
        "success": True,
        "data": {
            "items": [LeadListItem.model_validate(item).model_dump() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        "message": "ok",
    }


@router.post("")
def create_lead(
    body: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new lead."""
    # Validate status
    if body.status not in VALID_LEAD_STATUSES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的状态值: {body.status}，有效值为: {', '.join(sorted(VALID_LEAD_STATUSES))}",
        }

    # Validate intention_level
    if body.intention_level is not None and body.intention_level not in VALID_INTENTION_LEVELS:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的意向等级: {body.intention_level}，有效值为: {', '.join(sorted(VALID_INTENTION_LEVELS))}",
        }

    # Counselor cannot assign owner_id to someone else
    if current_user.role == "counselor" and body.owner_id is not None and body.owner_id != current_user.id:
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "咨询师只能创建自己负责的线索",
        }

    lead_data = body.model_dump()
    lead = lead_service.create_lead(db, lead_data, current_user)

    return {
        "success": True,
        "data": {"id": lead.id},
        "message": "线索创建成功",
    }


@router.get("/{lead_id}")
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get lead detail."""
    lead = lead_service.get_lead_by_id(db, lead_id)
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

    return {
        "success": True,
        "data": LeadResponse.model_validate(lead).model_dump(),
        "message": "ok",
    }


@router.put("/{lead_id}")
def update_lead(
    lead_id: int,
    body: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update lead (partial update)."""
    lead = lead_service.get_lead_by_id(db, lead_id)
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

    # Validate status if provided
    if body.status is not None and body.status not in VALID_LEAD_STATUSES:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的状态值: {body.status}，有效值为: {', '.join(sorted(VALID_LEAD_STATUSES))}",
        }

    # Validate intention_level if provided
    if body.intention_level is not None and body.intention_level not in VALID_INTENTION_LEVELS:
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": f"无效的意向等级: {body.intention_level}，有效值为: {', '.join(sorted(VALID_INTENTION_LEVELS))}",
        }

    # Counselor cannot reassign owner_id
    if current_user.role == "counselor" and body.owner_id is not None and body.owner_id != current_user.id:
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "咨询师不能将线索分配给其他人",
        }

    update_data = body.model_dump(exclude_unset=True)
    lead_service.update_lead(db, lead, update_data)

    return {
        "success": True,
        "data": {"id": lead.id},
        "message": "线索更新成功",
    }


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a lead."""
    lead = lead_service.get_lead_by_id(db, lead_id)
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

    lead_service.delete_lead(db, lead)

    return {
        "success": True,
        "data": None,
        "message": "线索已删除",
    }
