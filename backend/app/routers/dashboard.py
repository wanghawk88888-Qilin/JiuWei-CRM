from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import RecentLeadItem
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return dashboard summary statistics with role-based filtering."""
    summary = dashboard_service.get_dashboard_summary(db, current_user)
    return {
        "success": True,
        "data": summary,
        "message": "ok",
    }


@router.get("/today-followups")
def get_today_followups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return today's and overdue followups (max 20). Role-based filtering applied."""
    items = dashboard_service.get_today_followups(db, current_user)
    return {
        "success": True,
        "data": items,
        "message": "ok",
    }


@router.get("/recent-leads")
def get_recent_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the 10 most recently created leads. Role-based filtering applied."""
    leads = dashboard_service.get_recent_leads(db, current_user)
    return {
        "success": True,
        "data": [RecentLeadItem.model_validate(lead).model_dump() for lead in leads],
        "message": "ok",
    }
