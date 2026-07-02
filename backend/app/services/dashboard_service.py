import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.lead import Lead
from app.models.followup import FollowUp
from app.models.user import User


def _apply_lead_owner_filter(query, current_user: User):
    """Apply role-based owner filter to a Lead query.

    admin / manager: no filter (see all)
    counselor: only own leads (owner_id == current_user.id)
    """
    if current_user.role == "counselor":
        query = query.filter(Lead.owner_id == current_user.id)
    return query


def get_dashboard_summary(db: Session, current_user: User) -> dict:
    """Return dashboard summary statistics.

    Returns:
        dict with keys: total_leads, today_new_leads, pending_followups, enrolled_leads
    """

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    today_end = today_str + " 23:59:59"

    # Base query: non-deleted leads
    base = db.query(Lead).filter(Lead.deleted_at.is_(None))
    base = _apply_lead_owner_filter(base, current_user)

    # total_leads
    total_leads = base.count()

    # today_new_leads — created_at starts with today's date
    today_new_leads = base.filter(Lead.created_at.like(f"{today_str}%")).count()

    # enrolled_leads
    enrolled_leads = base.filter(Lead.status == "enrolled").count()

    # pending_followups — distinct leads that have a non-deleted followup
    # with next_followup_at <= today_end
    pending_query = (
        db.query(func.count(func.distinct(FollowUp.lead_id)))
        .join(Lead, FollowUp.lead_id == Lead.id)
        .filter(
            FollowUp.deleted_at.is_(None),
            FollowUp.next_followup_at.isnot(None),
            FollowUp.next_followup_at <= today_end,
            Lead.deleted_at.is_(None),
        )
    )
    pending_query = _apply_lead_owner_filter(pending_query, current_user)
    pending_followups = pending_query.scalar() or 0

    return {
        "total_leads": total_leads,
        "today_new_leads": today_new_leads,
        "pending_followups": pending_followups,
        "enrolled_leads": enrolled_leads,
    }


def get_today_followups(db: Session, current_user: User) -> list[dict]:
    """Return today's and overdue followups (max 20).

    Returns list of dicts with: lead_id, lead_name, phone, status,
    intention_level, next_followup_at, owner_id.
    Sorted by next_followup_at ASC.
    """

    today_end = datetime.datetime.now().strftime("%Y-%m-%d") + " 23:59:59"

    query = (
        db.query(
            FollowUp.lead_id,
            Lead.name.label("lead_name"),
            Lead.phone,
            Lead.status,
            Lead.intention_level,
            FollowUp.next_followup_at,
            Lead.owner_id,
        )
        .join(Lead, FollowUp.lead_id == Lead.id)
        .filter(
            FollowUp.deleted_at.is_(None),
            FollowUp.next_followup_at.isnot(None),
            FollowUp.next_followup_at <= today_end,
            Lead.deleted_at.is_(None),
        )
    )

    # Role-based filtering
    if current_user.role == "counselor":
        query = query.filter(Lead.owner_id == current_user.id)

    # Deduplicate by lead_id — keep the earliest next_followup_at per lead
    query = (
        query
        .order_by(FollowUp.next_followup_at.asc())
        .limit(20)
    )

    results = query.all()
    return [
        {
            "lead_id": row.lead_id,
            "lead_name": row.lead_name,
            "phone": row.phone,
            "status": row.status,
            "intention_level": row.intention_level,
            "next_followup_at": row.next_followup_at,
            "owner_id": row.owner_id,
        }
        for row in results
    ]


def get_recent_leads(db: Session, current_user: User) -> list[Lead]:
    """Return the 10 most recently created non-deleted leads."""

    query = (
        db.query(Lead)
        .filter(Lead.deleted_at.is_(None))
    )
    query = _apply_lead_owner_filter(query, current_user)

    return (
        query
        .order_by(Lead.created_at.desc())
        .limit(10)
        .all()
    )
