from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.lead import Lead
from app.models.followup import FollowUp
from app.models.user import User

from app.services import datetime_utils
from app.services.lead_service import latest_followup_next_at_subquery


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

    today_str = datetime_utils.business_today()
    today_end = today_str + " 23:59:59"

    # Base query: non-deleted leads
    base = db.query(Lead).filter(Lead.deleted_at.is_(None))
    base = _apply_lead_owner_filter(base, current_user)

    # total_leads
    total_leads = base.count()

    # today_new_leads — created_at (UTC) falls within the Beijing business day.
    utc_start, utc_end = datetime_utils.business_day_utc_range()
    today_new_leads = base.filter(
        Lead.created_at >= utc_start,
        Lead.created_at < utc_end,
    ).count()

    # enrolled_leads
    enrolled_leads = base.filter(Lead.status == "enrolled").count()

    # pending_followups — leads whose *latest* followup is due today or overdue;
    # enrolled / invalid leads are excluded so they no longer surface as "待跟进".
    effective = latest_followup_next_at_subquery(db)
    pending_query = (
        db.query(func.count(Lead.id))
        .filter(
            Lead.deleted_at.is_(None),
            Lead.status.notin_(["enrolled", "invalid"]),
            effective.isnot(None),
            effective <= today_end,
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
    """Return today's followups: overdue + due-today, sorted by urgency.

    The business definition of "今日待跟进" is:

      overdue  (effective next_followup_at < today)
      today    (effective next_followup_at == today, at any time)

    ``effective next_followup_at`` is the latest non-deleted followup's value
    (see ``latest_followup_next_at_subquery``). Tomorrow and later are excluded,
    as are enrolled / invalid and soft-deleted leads. No silent cap is applied —
    the list always matches the dashboard "待跟进" count.
    """

    today_str = datetime_utils.business_today()
    today_start = today_str + " 00:00:00"
    today_end = today_str + " 23:59:59"

    from app.models.course import Course

    # Effective next-followup time (latest followup, normalised) — shared with
    # the summary count and the lead list `followup=pending` filter.
    effective = latest_followup_next_at_subquery(db)

    # Correlated subquery: latest followup content for each lead
    latest_content_subq = (
        db.query(FollowUp.content)
        .filter(
            FollowUp.lead_id == Lead.id,
            FollowUp.deleted_at.is_(None),
        )
        .order_by(FollowUp.created_at.desc(), FollowUp.id.desc())
        .limit(1)
        .correlate(Lead)
        .scalar_subquery()
    )

    query = (
        db.query(
            Lead.id.label("lead_id"),
            Lead.name.label("lead_name"),
            Lead.phone,
            Lead.status,
            Lead.intention_level,
            effective.label("next_followup_at"),
            Lead.owner_id,
            User.real_name.label("owner_name"),
            Course.name.label("intended_course_name"),
            latest_content_subq.label("latest_followup_content"),
        )
        .outerjoin(Course, Lead.intended_course_id == Course.id)
        .outerjoin(User, Lead.owner_id == User.id)
        .filter(
            Lead.deleted_at.is_(None),
            Lead.status.notin_(["enrolled", "invalid"]),
            effective.isnot(None),
            effective <= today_end,
        )
    )

    # Role-based filtering
    if current_user.role == "counselor":
        query = query.filter(Lead.owner_id == current_user.id)

    results = query.all()

    # Build response with priority classification and content truncation
    items = []
    for row in results:
        # Classify priority — normalise so both "T" and space formats compare
        # correctly against the day boundaries.
        next_at = datetime_utils.normalize_datetime(row.next_followup_at) or ""
        priority = "overdue" if next_at < today_start else "today"

        # Truncate latest content for summary display
        content = row.latest_followup_content
        if content and len(content) > 50:
            content = content[:50] + "..."

        items.append({
            "lead_id": row.lead_id,
            "lead_name": row.lead_name,
            "phone": row.phone,
            "status": row.status,
            "intention_level": row.intention_level,
            "next_followup_at": row.next_followup_at,
            "owner_id": row.owner_id,
            "owner_name": row.owner_name,
            "intended_course_name": row.intended_course_name,
            "latest_followup_content": content,
            "followup_priority": priority,
        })

    # Sort: overdue → today, each group ASC by next_followup_at.
    priority_order = {"overdue": 0, "today": 1}
    items.sort(key=lambda x: (
        priority_order.get(x["followup_priority"], 9),
        datetime_utils.normalize_datetime(x["next_followup_at"]) or "",
    ))

    return items


def _enrich_owner_names(db: Session, leads: list[Lead]) -> None:
    """Attach owner_name (User.real_name) to each Lead object in-place."""
    if not leads:
        return
    owner_ids = {lead.owner_id for lead in leads if lead.owner_id is not None}
    owner_map: dict[int, str] = {}
    if owner_ids:
        users = db.query(User).filter(User.id.in_(owner_ids)).all()
        owner_map = {u.id: u.real_name for u in users}
    for lead in leads:
        lead.owner_name = (
            owner_map.get(lead.owner_id) if lead.owner_id is not None else None
        )


def get_recent_leads(db: Session, current_user: User) -> list[Lead]:
    """Return the 10 most recently created non-deleted leads."""

    query = (
        db.query(Lead)
        .filter(Lead.deleted_at.is_(None))
    )
    query = _apply_lead_owner_filter(query, current_user)

    leads = (
        query
        .order_by(Lead.created_at.desc())
        .limit(10)
        .all()
    )
    _enrich_owner_names(db, leads)
    return leads
